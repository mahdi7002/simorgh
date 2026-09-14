import os
import time
import wave

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from core.paths import AUDIO_OUT_DIR
from core.stt import transcribe
from core.chat import ask
from core.tts import synthesize

router = APIRouter()
VOICE_DIR = AUDIO_OUT_DIR / "voice_in"
VOICE_DIR.mkdir(parents=True, exist_ok=True)
MAX_VOICE_BYTES = int(os.getenv("SIMORGH_MAX_VOICE_BYTES", str(5 * 1024 * 1024)))


@router.post("/voice")
async def receive_voice(request: Request):
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_VOICE_BYTES:
                raise HTTPException(413, "Voice payload too large")
        except ValueError:
            raise HTTPException(400, "Invalid Content-Length")

    raw_pcm = await request.body()
    if len(raw_pcm) < 1000:
        raise HTTPException(400, "Voice data too small")
    if len(raw_pcm) > MAX_VOICE_BYTES:
        raise HTTPException(413, "Voice payload too large")

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
        return FileResponse(
            audio_out_path,
            media_type="audio/wav",
            headers={"X-SIMORGH-AI-GENERATED": "true"},
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    finally:
        wav_path.unlink(missing_ok=True)
