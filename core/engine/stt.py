import os, json, wave

try:
    import vosk
except ImportError:
    vosk = None

# مسیر مطلق به مدل Vosk (دقیقاً همان جایی که استخراج شده) — قابل override
MODEL_PATH = os.environ.get(
    "SIMORGH_VOSK_MODEL", os.path.expanduser("~/simorgh/models/vosk-model-fa")
)

_model = None

def _get_model():
    global _model
    if vosk is None:
        raise RuntimeError("پکیج vosk نصب نیست — pip install vosk")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"مدل Vosk در {MODEL_PATH} یافت نشد")
    if _model is None:
        _model = vosk.Model(MODEL_PATH)
    return _model

def transcribe_wav(wav_path: str) -> str:
    model = _get_model()
    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
        raise ValueError("فایل صوتی باید mono, 16bit, 16000Hz باشد")
    rec = vosk.KaldiRecognizer(model, 16000)
    results = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()).get("text", ""))
    results.append(json.loads(rec.FinalResult()).get("text", ""))
    wf.close()
    return " ".join(results).strip()
