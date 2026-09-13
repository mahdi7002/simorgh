import os, json, wave
import vosk

# مسیر مطلق به مدل Vosk (دقیقاً همان جایی که استخراج شده)
MODEL_PATH = os.path.expanduser("~/simorgh/models/vosk-model-fa")

_model = None

def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"مدل Vosk در {MODEL_PATH} یافت نشد")
        _model = vosk.Model(MODEL_PATH)
    return _model

def transcribe_wav(wav_path: str) -> str:
    model = get_model()
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
