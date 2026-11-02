"""Local transcription via mlx-whisper (Whisper on Apple MLX).

Benchmark M4 / voz real es (12-jul-2026), whisper-large-v3-turbo:
  ~950ms warm (10s audio) — mejor precision del stack, WER 2.9%, offline, $0.
  mlx-whisper cachea el modelo cargado por repo => llamadas repetidas van warm.

Changes vs upstream:
- WAV is decoded in Python (wave + numpy) and handed to mlx-whisper as an
  array. Upstream passed a file path, which makes mlx-whisper shell out to
  `ffmpeg`; a Finder-launched .app has no Homebrew on its PATH, so local
  transcription failed on Macs without ffmpeg in /usr/bin.
- The model is resolved from the local Hugging Face cache first, so after the
  first download it loads fully offline (no network check on every start).

Opcional: `pip install mlx-whisper` (Apple Silicon).
"""
import io
import wave

import numpy as np

from config import LOCAL_MODEL_ID, WHISPER_LANGUAGE

_TARGET_SR = 16000


def wav_bytes_to_float32(data: bytes) -> np.ndarray:
    """Decode a PCM WAV (8/16/24/32-bit, any rate, any channels) into mono
    float32 at 16 kHz, the format Whisper expects."""
    with wave.open(io.BytesIO(data), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if width == 1:
        audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        raw = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        ints = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8)
                | (raw[:, 2].astype(np.int32) << 16))
        ints = np.where(ints & 0x800000, ints - 0x1000000, ints)
        audio = ints.astype(np.float32) / 8388608.0
    elif width == 4:
        audio = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width: {width}")

    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)

    if rate != _TARGET_SR and audio.size:
        n_out = int(round(audio.size * _TARGET_SR / rate))
        x_old = np.linspace(0.0, 1.0, num=audio.size, endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        audio = np.interp(x_new, x_old, audio).astype(np.float32)

    return np.ascontiguousarray(audio, dtype=np.float32)


def resolve_model_path(repo_id: str) -> str:
    """Local snapshot path if the model is already cached, else the repo id
    (mlx-whisper downloads it on first use)."""
    try:
        from huggingface_hub import snapshot_download
        return snapshot_download(repo_id, local_files_only=True)
    except Exception:
        return repo_id


class LocalTranscriber:
    """mlx-whisper backend. Lazy-loads model + first-run downloads from HF.

    model_id es parametrizable (whisper-large-v3-turbo por defecto) para que el
    router pueda ofrecer distintos tamanos de Whisper desde Ajustes.
    """

    def __init__(self, model_id: str = LOCAL_MODEL_ID):
        self._model_id = model_id
        self._model_path: str | None = None
        self._tried_import = False
        self._import_error: str | None = None

    @property
    def available(self) -> bool:
        if not self._tried_import:
            try:
                import mlx_whisper  # noqa: F401
                self._tried_import = True
            except Exception as e:
                self._tried_import = True
                self._import_error = str(e)
                return False
        return self._import_error is None

    def _path(self) -> str:
        # Re-resolve until we have a real local path (first run downloads).
        if self._model_path is None or self._model_path == self._model_id:
            self._model_path = resolve_model_path(self._model_id)
        return self._model_path

    def warm(self):
        """Precarga el modelo en un audio de silencio para dejarlo residente."""
        if not self.available:
            return
        import mlx_whisper
        try:
            mlx_whisper.transcribe(
                np.zeros(1600, dtype=np.float32),  # 0.1s de silencio
                path_or_hf_repo=self._path(),
                language=WHISPER_LANGUAGE,
                temperature=0.0,
            )
        except Exception:
            pass

    def transcribe(self, wav_buffer: io.BytesIO, vocabulary_prompt: str = "") -> str:
        if not self.available:
            raise RuntimeError(f"mlx-whisper not available: {self._import_error}")

        import mlx_whisper

        wav_buffer.seek(0)
        data = wav_buffer.read()
        if len(data) < 100:
            return ""

        audio = wav_bytes_to_float32(data)
        if audio.size == 0:
            return ""

        kwargs = {
            "path_or_hf_repo": self._path(),
            "language": WHISPER_LANGUAGE,
            "temperature": 0.0,
        }
        if vocabulary_prompt:
            kwargs["initial_prompt"] = vocabulary_prompt
        result = mlx_whisper.transcribe(audio, **kwargs)
        # After a first-run download, switch to the local snapshot path.
        self._path()
        return (result.get("text") or "").strip()

    @property
    def model_id(self) -> str:
        return self._model_id
