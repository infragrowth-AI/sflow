#!/bin/bash
# uninstall.sh — remove SFlow for the current user.
#
#   ./uninstall.sh                 remove the app and start-at-login (keeps your history)
#   ./uninstall.sh --purge         ...and delete your data: history, recordings, settings, Groq key
#   ./uninstall.sh --remove-model  ...and delete the downloaded Whisper model (~1.6 GB)
#
# Environment (mostly for testing): SFLOW_PREFIX, SFLOW_LAUNCH_AGENTS_DIR,
# SFLOW_DATA_DIR (default: ~/Library/Application Support/SFlow).
#
# Only removes an app whose bundle ID is ai.infragrowth.sflow. The build
# folders in this repo (.venv, build, dist) stay; delete the repo folder to drop them.
set -euo pipefail

BUNDLE_ID="ai.infragrowth.sflow"
PREFIX="${SFLOW_PREFIX:-$HOME/Applications}"
DEST="$PREFIX/SFlow.app"
AGENTS_DIR="${SFLOW_LAUNCH_AGENTS_DIR:-$HOME/Library/LaunchAgents}"
PLIST="$AGENTS_DIR/$BUNDLE_ID.plist"
DATA_DIR="${SFLOW_DATA_DIR:-$HOME/Library/Application Support/SFlow}"
MODEL_DIR="${HF_HUB_CACHE:-$HOME/.cache/huggingface/hub}/models--mlx-community--whisper-large-v3-turbo"

PURGE=0
REMOVE_MODEL=0
for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=1 ;;
        --remove-model) REMOVE_MODEL=1 ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg"; exit 2 ;;
    esac
done

if pgrep -f "$DEST/Contents/MacOS/SFlow" >/dev/null 2>&1; then
    echo "Closing SFlow..."
    pkill -TERM -f "$DEST/Contents/MacOS/SFlow" || true
    sleep 1
    pkill -KILL -f "$DEST/Contents/MacOS/SFlow" 2>/dev/null || true
fi

if [ -f "$PLIST" ]; then
    if [ -z "${SFLOW_LAUNCH_AGENTS_DIR:-}" ]; then
        launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
    fi
    rm -f "$PLIST"
    echo "Removed start at login."
fi

if [ -d "$DEST" ]; then
    ID="$(defaults read "$DEST/Contents/Info" CFBundleIdentifier 2>/dev/null || true)"
    if [ "$ID" = "$BUNDLE_ID" ]; then
        rm -rf "$DEST"
        echo "Removed $DEST"
    else
        echo "Left $DEST alone: it is not this SFlow ($ID)."
    fi
else
    echo "No app at $DEST"
fi

if [ "$PURGE" -eq 1 ]; then
    if [ -d "$DATA_DIR" ]; then
        if [ -d "/Applications/SFlow.app" ] && [ -z "${SFLOW_DATA_DIR:-}" ]; then
            echo "NOTE: another SFlow in /Applications shares $DATA_DIR; its history goes too."
        fi
        rm -rf "$DATA_DIR"
        echo "Deleted your SFlow data ($DATA_DIR)."
    else
        echo "No data at $DATA_DIR"
    fi
else
    echo "Kept your history and settings in $DATA_DIR (use --purge to delete them)."
fi

if [ "$REMOVE_MODEL" -eq 1 ]; then
    if [ -d "$MODEL_DIR" ]; then
        rm -rf "$MODEL_DIR"
        echo "Deleted the Whisper model ($MODEL_DIR)."
    else
        echo "No model at $MODEL_DIR"
    fi
fi

echo
echo "SFlow may still be listed in System Settings > Privacy & Security"
echo "(Accessibility, Input Monitoring, Microphone). Select it and click - to tidy up."
