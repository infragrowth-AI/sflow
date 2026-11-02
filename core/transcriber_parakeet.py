"""Local transcription via parakeet-mlx (NVIDIA Parakeet on Apple MLX).

El motor mas RAPIDO del stack (mismo que usa Handy). Benchmark M4 (voz real es,
12-jul-2026): ~280ms warm en dictados cortos = ~25x realtime, offline, $0.
Trade-off: pierde precision en nombres propios / jerga vs Whisper Turbo, y NO
soporta hint de vocabulario (el diccionario personal se ignora aqui).

Modelo por defecto: mlx-community/parakeet-tdt-0.6b-v3 (multilingue, ~600MB).
El modelo se mantiene RESIDENTE tras el primer load (warm) para latencia minima.
Opcional: `pip install parakeet-mlx` (Apple Silicon).
"""
import io


class ParakeetTranscriber:
    """parakeet-mlx backend. Lazy-load + modelo residente."""

    def __init__(self, model_id: str = "mlx-community/parakeet-tdt-0.6b-v3"):
        self._model_id = model_id
        self._model = None
        self._tried_import = False
        self._import_error: str | None = None

    @property
    def available(self) -> bool:
        if not self._tried_import:
            self._tried_import = True
            try:
                import parakeet_mlx  # noqa: F401
            except Exception as e:
                self._import_error = str(e)
        return self._import_error is None

    def _ensure_model(self):
        if self._model is None:
            from parakeet_mlx import from_pretrained
            self._model = from_pretrained(self._model_id)
        return self._model

    def warm(self):
        """Precarga el modelo (llamar al arranque para que el 1er dictado sea warm)."""
        if self.available:
            self._ensure_model()

    def transcribe(self, wav_buffer: io.BytesIO, vocabulary_prompt: str = "") -> str:
        # vocabulary_prompt se ignora: Parakeet no acepta hint de vocabulario.
        if not self.available:
            raise RuntimeError(f"parakeet-mlx not available: {self._import_error}")

        wav_buffer.seek(0)
        data = wav_buffer.read()
        if len(data) < 100:
            return ""

        # Decode in Python and feed the array straight to the model: upstream
        # passed a file path, which makes parakeet-mlx shell out to ffmpeg
        # (missing on a Finder-launched .app's PATH).
        import mlx.core as mx
        from parakeet_mlx.audio import get_logmel
        from core.transcriber_local import wav_bytes_to_float32

        audio = wav_bytes_to_float32(data)
        model = self._ensure_model()
        if audio.size < model.preprocessor_config.hop_length:
            return ""
        mel = get_logmel(mx.array(audio), model.preprocessor_config)
        result = model.generate(mel)[0]
        return (getattr(result, "text", "") or "").strip()

    @property
    def model_id(self) -> str:
        return self._model_id
