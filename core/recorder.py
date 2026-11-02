import io
import wave
import queue
import time
import numpy as np
import sounddevice as sd
from config import SAMPLE_RATE, CHANNELS, AUDIO_DTYPE, BLOCK_SIZE


# Avoid Bluetooth mics (AirPods, Bose, Beats, etc). Opening their input forces
# macOS to switch the headphones from A2DP (hi-fi stereo) to HFP (mono call
# mode), which emits an audible "call ended" beep when the stream closes.
# By pinning input to the built-in mic, the headphones stay in A2DP the whole
# time and output audio uninterrupted.
_PREFER_INPUT_KEYWORDS = ("macbook", "built-in", "builtin", "internal", "mac mini")
_AVOID_INPUT_KEYWORDS = (
    "airpods", "bose", "beats", "sony", "sennheiser",
    "jabra", "jbl", "wireless", "bluetooth", " bt ",
)


def _pick_input_device() -> int | None:
    try:
        devices = sd.query_devices()
    except Exception:
        return None

    candidates = [
        (i, d) for i, d in enumerate(devices)
        if d.get("max_input_channels", 0) > 0
    ]
    if not candidates:
        return None

    for idx, dev in candidates:
        name = dev["name"].lower()
        if any(kw in name for kw in _PREFER_INPUT_KEYWORDS):
            return idx

    for idx, dev in candidates:
        name = dev["name"].lower()
        if not any(kw in name for kw in _AVOID_INPUT_KEYWORDS):
            return idx

    return None  # let sounddevice use system default


class AudioRecorder:
    def __init__(self):
        self.audio_queue = queue.Queue()  # For UI visualization
        self.frames: list[np.ndarray] = []
        self.stream: sd.InputStream | None = None
        self.is_recording = False
        self._start_time = 0.0
        self._input_device = _pick_input_device()
        try:
            if self._input_device is not None:
                name = sd.query_devices(self._input_device)["name"]
                print(f"[recorder] input device: [{self._input_device}] {name}")
            else:
                print("[recorder] input device: system default")
        except Exception:
            pass

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())
        self.frames.append(indata.copy())

    def start(self):
        self.frames.clear()
        # Drain any old data from the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.is_recording = True
        self._start_time = time.time()
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=AUDIO_DTYPE,
            blocksize=BLOCK_SIZE,
            callback=self._callback,
            device=self._input_device,
        )
        self.stream.start()

    def stop(self) -> float:
        """Stop recording and return duration in seconds."""
        self.is_recording = False
        duration = time.time() - self._start_time
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        return duration

    def get_wav_buffer(self) -> io.BytesIO:
        """Convert recorded frames to in-memory WAV buffer."""
        if not self.frames:
            return io.BytesIO()
        audio_data = np.concatenate(self.frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        buf.seek(0)
        return buf

    def save_wav_to(self, path: str) -> str | None:
        """Write the current recording to disk at `path`. Returns path on success."""
        if not self.frames:
            return None
        audio_data = np.concatenate(self.frames, axis=0)
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())
        return path

    def get_duration(self) -> float:
        if not self.frames:
            return 0.0
        total_samples = sum(f.shape[0] for f in self.frames)
        return total_samples / SAMPLE_RATE
