# AGENTS.md — installing SFlow on someone's Mac

You are an AI assistant (Claude Code, Codex, or similar) and the user asked you to install
SFlow. The user is usually **not technical**: a consultant or agency owner. Talk to them in
their language (most speak Spanish; use plain words, no jargon). Run every command yourself;
only ask them to do what only a human can do (click a switch in System Settings, press a
shortcut, speak).

SFlow is a macOS menu-bar app: hold **Control + Option**, speak, release, and the text is
typed where the cursor is. It transcribes locally with Whisper (MLX) on Apple Silicon.

## Ground rules

- **Never ask for, print, store or commit an API key.** SFlow works without any key on
  Apple Silicon. If the user wants Groq (cloud engine, LLM cleanup, Option+1…8 transforms),
  they paste the key themselves in the app: menu bar icon → Ajustes → "Clave de Groq" →
  Guardar ajustes. If they paste a key in the chat anyway, tell them not to, don't repeat
  it, and suggest they rotate it at console.groq.com/keys.
- **No sudo.** Everything installs in the user's home (`~/Applications/SFlow.app`).
- **Don't touch another SFlow.** If `/Applications/SFlow.app` exists with a different
  bundle ID (another SFlow version), leave it. Only ask the user to quit it, because both
  apps listen to the same shortcut.
- **You don't flip privacy switches.** You open the right pane (`scripts/permissions.sh`)
  and the user clicks. One permission at a time; wait for "listo" before the next.
- **Don't rebuild without a reason.** Each rebuild changes the ad-hoc signature and macOS
  revokes Accessibility / Input Monitoring. `install.sh` already skips the build and the
  copy when nothing changed.

## Procedure

1. **Check the Mac.** `sw_vers -productVersion` must be 15 or newer. `sysctl -n
   hw.optional.arm64` = `1` means Apple Silicon. On Intel, explain that SFlow will need a
   Groq key (free tier) and that the audio goes to Groq; continue only if they agree.
2. **Get the code.** If `~/sflow` doesn't exist:
   `git clone https://github.com/infragrowth-AI/sflow.git ~/sflow`. If macOS offers to
   install the command line developer tools, tell the user to click "Instalar", wait,
   then retry. Keep `~/sflow`: updates and uninstall run from there.
3. **Another SFlow?** `pgrep -fl SFlow.app`. If one is running from somewhere other than
   `~/Applications/SFlow.app`, ask the user to quit it (menu bar icon → Salir).
4. **Ask once:** "¿Querés que SFlow arranque solo cuando prendés la Mac?" Yes → add `--login`.
5. **Install:** `cd ~/sflow && ./install.sh --no-launch [--login]`. First run takes
   10–20 minutes (≈2 GB of dependencies, a few minutes of build, and the 1.6 GB model
   download during the check). Use a long timeout or run it in the background. It checks
   the Mac, installs `uv` if missing (Homebrew if present, otherwise the official installer
   into `~/.local/bin`), creates `.venv` with Python 3.12, builds with PyInstaller, signs
   ad-hoc, installs to `~/Applications/SFlow.app` and runs the headless check.
6. **Verify:** `~/sflow/scripts/verify.sh` must end with `VERIFY: PASS`. It transcribes a
   Spanish phrase generated with `say`, offline, inside the built app, with no microphone
   and no permissions. Don't continue on a FAIL; see Troubleshooting.
7. **Permissions first, with SFlow closed** (one at a time; explain each in one sentence,
   open the pane, wait for "listo"). Granting them before the first launch is what works:
   launching without Accessibility makes macOS show its prompt and Settings at once, and
   the user gets lost or stuck. Make sure it is closed:
   `pkill -f "$HOME/Applications/SFlow.app/Contents/MacOS/SFlow" || true`.
   1. Accessibility — "para que SFlow pueda escribir donde está tu cursor":
      `scripts/permissions.sh accessibility`. Have them remove every "SFlow" entry with "–"
      (old builds stay listed and look identical), then "+", **Cmd + Shift + G**, paste
      `~/Applications/SFlow.app`, "Abrir", and turn it on.
   2. Input Monitoring — "para que SFlow sepa que apretaste el atajo":
      `scripts/permissions.sh input` (users can't find this pane on their own). Same: remove
      old "SFlow" entries, add `~/Applications/SFlow.app`, turn it on. If macOS offers
      "Salir y volver a abrir", they pick "Más tarde": you open it next.
8. **Open it:** `open ~/Applications/SFlow.app`. A small icon appears in the menu bar and
   a pill at the bottom of the screen. Check `~/Library/Application Support/SFlow/hotkey.log`
   gets a new `keyboard.Listener started` line.
   - Microphone — macOS asks on the first dictation; the user clicks "Permitir".
9. **Live test:** ask the user to open Notes (or any text field), click inside, hold
   **Control + Option**, say one sentence, and release. Ask whether the text appeared.
   The first dictation can take a few seconds while the model loads.

**Done** = `scripts/verify.sh` printed `VERIFY: PASS` **and** the user confirmed that a
dictated sentence appeared in a text field. Tell them the two shortcuts (hold Control +
Option; double-tap Control for hands-free, tap again to stop) and that clicking the menu
bar icon shows the history.

## Troubleshooting

Logs: `~/Library/Application Support/SFlow/sflow.log` (pipeline) and `hotkey.log`
(shortcut). They contain fragments of what the user dictated: read them, don't paste them
back to the chat beyond what's needed.

| Symptom | Likely cause | Fix |
|---|---|---|
| Shortcut does nothing; `hotkey.log` has no `emit pressed` | Input Monitoring (or Accessibility) missing | `scripts/permissions.sh input`, then restart SFlow |
| Pill records and shows a check, but no text appears | Accessibility missing or stale | `scripts/permissions.sh accessibility`; remove SFlow with "–", add it again with "+", restart |
| Worked before, stopped after an update/rebuild | New ad-hoc signature, macOS dropped the grants | Same as above, in both Accessibility and Input Monitoring |
| Pill shows a red X right away / "No speech detected" in the log | Microphone denied, or wrong input device | `scripts/permissions.sh microphone`; SFlow prefers the built-in mic and avoids Bluetooth headsets |
| First dictation takes long or fails; log mentions Hugging Face | Model (1.6 GB) not downloaded yet / no internet | Run `scripts/verify.sh` with internet; it downloads into `~/.cache/huggingface` |
| `VERIFY: FAIL` with `ConnectError` / `nodename nor servname` | Network or DNS dropped during the model download | Re-run `scripts/verify.sh` (or `./install.sh`, which retries 3 times); a VPN or flaky DNS is the usual cause |
| Text appears twice or odd behavior | Another SFlow running | Quit the other one |
| `install.sh` build step fails | See `~/sflow/build/pyinstaller.log`; often disk space | Free space (needs ~6 GB), re-run `./install.sh` |
| `VERIFY: FAIL (no Spanish voice...)` | The `say` voice is missing | System Settings → Accessibility → Spoken Content → add a Spanish voice |
| Intel Mac: nothing transcribes | No local engine | User pastes a Groq key in Ajustes → Clave de Groq, selects Groq |
| Paste works in most apps but not one | That field rejects synthetic typing | Ajustes → Inserción de texto → "Clipboard + Cmd+V" |

## Update and uninstall

- Update: `cd ~/sflow && git pull && ./install.sh --no-launch` then `open ~/Applications/SFlow.app`.
  If something changed, permissions must be granted again (step 7).
- Uninstall: `cd ~/sflow && ./uninstall.sh` (app + start at login, keeps history).
  `--purge` also deletes history, recordings, settings and the Groq key
  (`~/Library/Application Support/SFlow`); `--remove-model` deletes the 1.6 GB model.
  Then the user can delete `~/sflow` and remove SFlow from the Privacy lists with "–".

## For developers

- Run from source: `.venv/bin/python main.py`. Self-test from source: `scripts/verify.sh --dev`.
- `install.sh` env vars for testing without touching the real install:
  `SFLOW_PREFIX=/tmp/x/Applications SFLOW_LAUNCH_AGENTS_DIR=/tmp/x/LaunchAgents ./install.sh --no-launch`;
  `uninstall.sh` also honors `SFLOW_DATA_DIR`.
- Dependencies are pinned in `requirements.lock` (`uv pip compile requirements.txt
  --universal --python-version 3.12 -o requirements.lock`).
- Bundle ID and LaunchAgent label: `ai.infragrowth.sflow`.
