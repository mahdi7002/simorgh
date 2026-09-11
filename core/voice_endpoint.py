import time
import wave
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from core.paths import AUDIO_OUT_DIR
from core.stt import transcribe
from core.chat import ask
from core.tts import synthesize

router = APIRouter()
VOICE_DIR = AUDIO_OUT_DIR / "voice_in"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/voice")
async def receive_voice(request: Request):
    raw_pcm = await request.body()
    if len(raw_pcm) < 1000:
        raise HTTPException(400, "Voice data too small")
    wav_path = VOICE_DIR / f"voice_{time.time_ns()}.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_pcm)
    try:
        user_text = transcribe(str(wav_path)).strip()
        if not user_text:
            raise HTTPException(422, "چیزی شنیده نشد")
        response_text = ask(user_text, agent="hakim")
        audio_out_path = synthesize(response_text)
        return FileResponse(audio_out_path, media_type="audio/wav", headers={"X-User-Text": user_text[:200], "X-Response-Text": response_text[:200]})
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    finally:
        wav_path.unlink(missing_ok=True)
