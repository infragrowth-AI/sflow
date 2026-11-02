#!/bin/bash
# install.sh — build SFlow from this folder and install it for the current user.
#
#   ./install.sh               build (if needed), install to ~/Applications, verify, open the app
#   ./install.sh --login       ...and start SFlow when you log in
#   ./install.sh --no-launch   don't open the app or System Settings at the end
#   ./install.sh --skip-verify don't run the headless transcription check
#
# Environment (mostly for testing):
#   SFLOW_PREFIX              install folder (default: ~/Applications). No sudo needed.
#   SFLOW_LAUNCH_AGENTS_DIR   where the start-at-login file goes (default:
#                             ~/Library/LaunchAgents). When set, launchctl is not called.
#
# Safe to run again: if nothing changed it skips the build and the copy, so
# macOS keeps the permissions you already granted. A real rebuild changes the
# app's (ad-hoc) signature and macOS asks for Accessibility / Input Monitoring again.
set -euo pipefail

BUNDLE_ID="ai.infragrowth.sflow"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${SFLOW_PREFIX:-$HOME/Applications}"
DEST="$PREFIX/SFlow.app"
AGENTS_DIR="${SFLOW_LAUNCH_AGENTS_DIR:-$HOME/Library/LaunchAgents}"
PLIST="$AGENTS_DIR/$BUNDLE_ID.plist"

WANT_LOGIN=0
LAUNCH=1
VERIFY=1
for arg in "$@"; do
    case "$arg" in
        --login) WANT_LOGIN=1 ;;
        --no-launch) LAUNCH=0 ;;
        --skip-verify) VERIFY=0 ;;
        -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg (see ./install.sh --help)"; exit 2 ;;
    esac
done

say_step() { printf '\n==> %s\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

cd "$REPO_DIR"

# --- 1. This Mac ------------------------------------------------------------
say_step "Checking this Mac"
[ "$(uname -s)" = "Darwin" ] || fail "SFlow only runs on macOS."
MACOS_VERSION="$(sw_vers -productVersion)"
MACOS_MAJOR="${MACOS_VERSION%%.*}"
[ "$MACOS_MAJOR" -ge 15 ] || fail "SFlow needs macOS 15 (Sequoia) or newer. This Mac has $MACOS_VERSION."
echo "macOS $MACOS_VERSION"

# A Terminal running under Rosetta reports x86_64 on an Apple Silicon Mac:
# re-run natively so the local (MLX) engine gets installed.
if [ "$(uname -m)" != "arm64" ] && [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
    echo "Terminal is running under Rosetta; re-running as Apple Silicon."
    exec arch -arm64 /bin/bash "$0" "$@"
fi
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
    echo "Apple Silicon: local transcription (free, offline)."
else
    echo "WARNING: Intel Mac. The local engine needs Apple Silicon, so SFlow will use"
    echo "         Groq (cloud). You'll need a free Groq key, pasted in the app's own window."
fi

AVAIL_GB="$(df -g "$HOME" | awk 'NR==2 {print $4}')"
[ "${AVAIL_GB:-0}" -ge 6 ] || fail "Need about 6 GB free on disk (have ${AVAIL_GB} GB)."

# --- 2. uv (brings its own Python 3.12; no system Python needed) -----------
say_step "Python toolchain (uv)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo "Installing uv with Homebrew..."
        brew install uv
    else
        echo "Installing uv (official installer, into ~/.local/bin, no admin password)..."
        curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
    fi
fi
command -v uv >/dev/null 2>&1 || fail "Could not install uv. See https://docs.astral.sh/uv/"
echo "$(uv --version)"

# --- 3. Python environment --------------------------------------------------
say_step "Python 3.12 environment and dependencies (first time: ~2 GB, a few minutes)"
VENV_PY="$REPO_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ] || ! "$VENV_PY" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' 2>/dev/null; then
    uv venv --python 3.12 --python-preference only-managed --clear "$REPO_DIR/.venv"
fi
# portaudio (microphone) ships inside the sounddevice wheel: no `brew install portaudio`.
uv pip sync --python "$VENV_PY" requirements.lock
echo "Dependencies OK."

# --- 4. Build (skipped when the sources didn't change) ----------------------
say_step "Building SFlow.app"
STAMP="$(find . \( -path ./.venv -o -path ./build -o -path ./dist -o -path ./.git \) -prune -o \
    -type f \( -name '*.py' -o -name '*.spec' -o -name 'requirements.lock' -o -name '*.png' -o -name '*.icns' \) \
    -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 | shasum -a 256 | cut -c1-16)"
BUILT_STAMP_FILE="dist/SFlow.app/Contents/Resources/sflow-build-stamp"
if [ -f "$BUILT_STAMP_FILE" ] && [ "$(cat "$BUILT_STAMP_FILE")" = "$STAMP" ] \
    && codesign --verify --deep --strict dist/SFlow.app >/dev/null 2>&1; then
    echo "Already built from these sources ($STAMP). Skipping the build."
else
    mkdir -p build
    printf '%s' "$STAMP" > build/sflow-build-stamp
    echo "Building (takes a few minutes)..."
    if ! "$REPO_DIR/.venv/bin/pyinstaller" sflow.spec --noconfirm --clean \
        --distpath dist --workpath build/pyinstaller > build/pyinstaller.log 2>&1; then
        tail -30 build/pyinstaller.log
        fail "Build failed. Full log: $REPO_DIR/build/pyinstaller.log"
    fi
    # Ad-hoc signature (no Apple developer account). macOS ties permissions to it.
    # The identifier comes from CFBundleIdentifier (ai.infragrowth.sflow).
    codesign --force --deep --sign - dist/SFlow.app
    codesign --verify --deep --strict dist/SFlow.app || fail "Signature check failed."
    [ "$(codesign -dv dist/SFlow.app 2>&1 | sed -n 's/^Identifier=//p')" = "$BUNDLE_ID" ] \
        || fail "Unexpected signing identifier."
    [ "$(cat "$BUILT_STAMP_FILE" 2>/dev/null)" = "$STAMP" ] || fail "Build stamp missing in the bundle."
    echo "Built: $REPO_DIR/dist/SFlow.app ($(du -sh dist/SFlow.app | cut -f1))"
fi

# --- 5. Install --------------------------------------------------------------
say_step "Installing to $DEST"
case "$DEST" in */SFlow.app) ;; *) fail "Refusing to install to $DEST" ;; esac
mkdir -p "$PREFIX"
INSTALLED_STAMP="$(cat "$DEST/Contents/Resources/sflow-build-stamp" 2>/dev/null || true)"
if [ "$INSTALLED_STAMP" = "$STAMP" ]; then
    echo "Already installed and up to date. Not touching it (your permissions stay)."
else
    if [ -d "$DEST" ]; then
        OLD_ID="$(defaults read "$DEST/Contents/Info" CFBundleIdentifier 2>/dev/null || true)"
        [ "$OLD_ID" = "$BUNDLE_ID" ] || fail "$DEST exists and is not this SFlow ($OLD_ID). Move it away first."
        if pgrep -f "$DEST/Contents/MacOS/SFlow" >/dev/null 2>&1; then
            echo "Closing the running SFlow..."
            pkill -TERM -f "$DEST/Contents/MacOS/SFlow" || true
            sleep 1
            pkill -KILL -f "$DEST/Contents/MacOS/SFlow" 2>/dev/null || true
        fi
        rm -rf "$DEST"
        echo "Updated. macOS will ask for Accessibility and Input Monitoring again (new build)."
    fi
    ditto dist/SFlow.app "$DEST"
    echo "Installed."
fi

if [ -d "/Applications/SFlow.app" ]; then
    OTHER_ID="$(defaults read /Applications/SFlow.app/Contents/Info CFBundleIdentifier 2>/dev/null || true)"
    if [ "$OTHER_ID" != "$BUNDLE_ID" ]; then
        echo "NOTE: there is another SFlow in /Applications ($OTHER_ID). This installer does not touch it."
        echo "      Don't run both at once: they would listen to the same shortcut."
    fi
fi

# --- 6. Verify ---------------------------------------------------------------
if [ "$VERIFY" -eq 1 ]; then
    say_step "Checking it transcribes (headless; first time downloads the ~1.6 GB model)"
    if [ "$ARCH" = "arm64" ]; then
        # The 1.6 GB download can die on a flaky connection; try a few times.
        ok=0
        for attempt in 1 2 3; do
            if "$REPO_DIR/scripts/verify.sh" "$DEST"; then ok=1; break; fi
            echo "Attempt $attempt failed. Retrying..."
        done
        [ "$ok" -eq 1 ] || fail "Self-test failed 3 times (see above). Check the internet connection and re-run ./install.sh."
    else
        echo "Skipped on Intel: there is no local engine to test."
    fi
fi

# --- 7. Start at login (optional) -------------------------------------------
if [ "$WANT_LOGIN" -eq 1 ]; then
    say_step "Start at login"
    mkdir -p "$AGENTS_DIR"
    cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$BUNDLE_ID</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DEST/Contents/MacOS/SFlow</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLIST
    plutil -lint "$PLIST" >/dev/null || fail "Bad start-at-login file."
    # macOS loads ~/Library/LaunchAgents at the next login; we don't call
    # launchctl now so it never starts a second copy. Same file the app's
    # "Iniciar con macOS" menu toggle uses.
    echo "SFlow will start when you log in ($PLIST)."
fi

# --- 8. Open it and permissions ----------------------------------------------
if [ "$LAUNCH" -eq 1 ]; then
    # Permissions BEFORE the first launch: opening SFlow without Accessibility makes
    # macOS show its prompt and Settings at once, and users got stuck (2026-11-02).
    say_step "Permissions (SFlow stays closed until you grant them)"
    pkill -f "$DEST/Contents/MacOS/SFlow" 2>/dev/null || true
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" || true
    cat <<TXT

macOS needs two permissions before SFlow opens. In each list, remove any old
"SFlow" with "–", then "+", Cmd + Shift + G, paste $DEST, "Open", turn it on.

  1. Accessibility (open now) -> lets SFlow type where your cursor is.
  2. Input Monitoring -> lets SFlow hear the Control + Option shortcut.
       scripts/permissions.sh input
     If macOS offers "Quit & Reopen", pick "Later".

Then open SFlow:  open "$DEST"
Click in any text field, hold Control + Option, speak, release.
The first time, macOS asks for the Microphone: click "Allow".
TXT
else
    echo
    echo "Done. Open it with: open \"$DEST\""
fi
