from faster_whisper import WhisperModel

_model = None

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path: str) -> str:
    model = get_model()
    segments, _ = model.transcribe(audio_path, language="fa")
    return " ".join(seg.text.strip() for seg in segments)
