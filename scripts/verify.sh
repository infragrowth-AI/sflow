#!/bin/bash
# verify.sh — headless check that SFlow transcribes locally. No GUI, no
# permissions, no microphone, no Groq. Exit 0 = PASS.
#
#   scripts/verify.sh                 # checks the installed app
#   scripts/verify.sh /path/SFlow.app # checks a specific app bundle
#   scripts/verify.sh --dev           # checks the source tree (.venv)
#
# It generates a Spanish test phrase with macOS `say`, converts it to a 16 kHz
# mono WAV with `afconvert`, runs `SFlow --self-test <wav>` with a minimal PATH
# (like an app opened from Finder, so no Homebrew tools) and a throwaway data
# dir, and checks the transcript contains the expected words.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PHRASE="Hola, esto es una prueba de dictado"
EXPECT=(prueba dictado)

if [ "${1:-}" = "--dev" ]; then
    CMD=("$REPO_DIR/.venv/bin/python" "$REPO_DIR/main.py")
    [ -x "${CMD[0]}" ] || { echo "VERIFY: FAIL (no .venv; run ./install.sh first)"; exit 1; }
else
    APP="${1:-${SFLOW_PREFIX:-$HOME/Applications}/SFlow.app}"
    CMD=("$APP/Contents/MacOS/SFlow")
    [ -x "${CMD[0]}" ] || { echo "VERIFY: FAIL (no app at $APP)"; exit 1; }
fi

TMP="$(mktemp -d -t sflow-verify)"
trap 'rm -rf "$TMP"' EXIT

# Pick a Spanish voice that exists on this Mac.
VOICE=""
for v in "Paulina" "Mónica" "Eddy (Español (México))" "Eddy (Español (España))"; do
    if say -v '?' | grep -q "^$v "; then VOICE="$v"; break; fi
done
if [ -z "$VOICE" ]; then
    VOICE="$(say -v '?' | grep -E ' es_[A-Z]{2} ' | head -1 | sed -E 's/ +es_[A-Z]{2} .*//')"
fi
if [ -z "$VOICE" ]; then
    echo "VERIFY: FAIL (no Spanish voice for 'say'; add one in System Settings > Accessibility > Spoken Content)"
    exit 1
fi

say -v "$VOICE" -o "$TMP/phrase.aiff" "$PHRASE"
afconvert -f WAVE -d LEI16@16000 -c 1 "$TMP/phrase.aiff" "$TMP/phrase.wav"
echo "[verify] voice=$VOICE wav=16kHz mono"

# Keep only what a Finder-launched app would have, plus proxy / model-cache settings.
KEEP=(HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" SFLOW_DATA_DIR="$TMP/data")
for var in HTTPS_PROXY HTTP_PROXY NO_PROXY https_proxy http_proxy no_proxy HF_HOME HF_HUB_CACHE; do
    if [ -n "${!var:-}" ]; then KEEP+=("$var=${!var}"); fi
done

set +e
env -i "${KEEP[@]}" "${CMD[@]}" --self-test "$TMP/phrase.wav" 2>"$TMP/stderr.log" | tee "$TMP/out.log"
CODE=${PIPESTATUS[0]}
set -e

if [ "$CODE" -eq 3 ]; then
    echo "VERIFY: FAIL (local engine not available on this Mac: Intel or MLX missing; use Groq in the app's settings)"
    exit 3
fi
if [ "$CODE" -ne 0 ]; then
    echo "[verify] last stderr lines:"; tail -20 "$TMP/stderr.log" || true
    echo "VERIFY: FAIL (self-test exit $CODE)"
    exit 1
fi

TEXT="$(grep '^\[self-test\] TEXT:' "$TMP/out.log" | sed 's/^\[self-test\] TEXT: //' \
    | tr '[:upper:]' '[:lower:]' | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || true)"
for w in "${EXPECT[@]}"; do
    if ! grep -q "$w" <<<"$TEXT"; then
        echo "VERIFY: FAIL (transcript is missing \"$w\")"
        exit 1
    fi
done
echo "VERIFY: PASS"
