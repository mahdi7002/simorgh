# -*- coding: utf-8 -*-
_model = None
_err = None
try:
    from faster_whisper import WhisperModel
except Exception as e:
    WhisperModel = None
    _err = e

def available():
    return WhisperModel is not None

def get_model():
    global _model
    if not available():
        raise RuntimeError("pip install faster-whisper") from _err
    if _model is None:
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def transcribe(audio_path: str) -> str:
    segments, _ = get_model().transcribe(audio_path, language="fa")
    return " ".join(s.text.strip() for s in segments)
