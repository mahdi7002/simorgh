try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

_model = None

def get_model():
    global _model
    if WhisperModel is None:
        raise RuntimeError(
            "faster-whisper نصب نیست — برای فعال‌سازی گفتار-به-متن: "
            "pip install faster-whisper"
        )
    if _model is None:
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path: str) -> str:
    model = get_model()
    segments, _ = model.transcribe(audio_path, language="fa")
    return " ".join(seg.text.strip() for seg in segments)
