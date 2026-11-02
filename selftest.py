"""Headless self-test: transcribe one WAV with the LOCAL engine and exit.

    SFlow.app/Contents/MacOS/SFlow --self-test <file.wav>
    python main.py --self-test <file.wav>

No GUI, no hotkeys, no microphone, no macOS permissions, no network calls
except the one-time model download if it is not cached yet. It never uses Groq,
so a pass proves the offline engine works inside the built binary.

Exit codes: 0 = transcribed non-empty text, 1 = empty/failed, 2 = bad usage,
3 = local engine not available on this Mac (Intel or MLX missing).
"""
import os
import sys
import time


def run(argv: list[str]) -> int:
    try:
        wav_path = argv[argv.index("--self-test") + 1]
    except (ValueError, IndexError):
        print("usage: SFlow --self-test <file.wav>", file=sys.stderr)
        return 2
    if not os.path.isfile(wav_path):
        print(f"[self-test] file not found: {wav_path}", file=sys.stderr)
        return 2

    from config import LOCAL_MODEL_ID, APP_DATA_DIR
    from core.transcriber_local import LocalTranscriber, resolve_model_path

    print(f"[self-test] frozen={bool(getattr(sys, 'frozen', False))} data_dir={APP_DATA_DIR}")

    try:
        import sounddevice as sd
        print(f"[self-test] portaudio={sd.get_portaudio_version()[1]}")
    except Exception as e:  # audio capture would fail in the app too
        print(f"[self-test] portaudio FAIL {type(e).__name__}: {e}")
        return 1

    engine = LocalTranscriber(LOCAL_MODEL_ID)
    if not engine.available:
        print(f"[self-test] local engine not available: {engine._import_error}")
        print("[self-test] RESULT: NO_LOCAL_ENGINE")
        return 3

    cached = resolve_model_path(LOCAL_MODEL_ID) != LOCAL_MODEL_ID
    print(f"[self-test] engine=mlx-whisper model={LOCAL_MODEL_ID} cached={cached}")
    if not cached:
        print("[self-test] downloading the model once (~1.6 GB), this can take a few minutes...")

    with open(wav_path, "rb") as f:
        import io
        buf = io.BytesIO(f.read())

    t0 = time.perf_counter()
    try:
        text = engine.transcribe(buf)
    except Exception as e:
        print(f"[self-test] FAIL {type(e).__name__}: {e}")
        print("[self-test] RESULT: FAIL")
        return 1
    elapsed = time.perf_counter() - t0

    print(f"[self-test] seconds={elapsed:.1f}")
    print(f"[self-test] TEXT: {text}")
    ok = bool(text.strip())
    print(f"[self-test] RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1
