#!/bin/bash
# permissions.sh — open ONE macOS privacy pane for SFlow, with plain instructions.
#
#   scripts/permissions.sh accessibility   # typing the text where the cursor is
#   scripts/permissions.sh input           # hearing the keyboard shortcut
#   scripts/permissions.sh microphone      # recording your voice
#
# It only opens System Settings; you flip the switch yourself.
set -euo pipefail

APP="${SFLOW_PREFIX:-$HOME/Applications}/SFlow.app"

case "${1:-}" in
    accessibility)
        PANE="Privacy_Accessibility"
        TEXT="Accessibility: turn on \"SFlow\". If it is not in the list, click +, and pick $APP.
If it is already on but pasting doesn't work (e.g. after an update), select it, click -, and add it again." ;;
    input)
        PANE="Privacy_ListenEvent"
        TEXT="Input Monitoring: turn on \"SFlow\". If it is not in the list, click +, and pick $APP.
Then quit SFlow from its menu bar icon and open it again." ;;
    microphone)
        PANE="Privacy_Microphone"
        TEXT="Microphone: turn on \"SFlow\". (It only appears after SFlow tried to record once.)" ;;
    *)
        sed -n '2,8p' "$0"; exit 2 ;;
esac

open "x-apple.systempreferences:com.apple.preference.security?$PANE"
echo "Opened System Settings > Privacy & Security."
echo "$TEXT"
