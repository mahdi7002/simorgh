from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os, time, logging, wave

logger = logging.getLogger(__name__)
router = APIRouter()

VOICE_DIR = "/tmp/simorgh_voice"
os.makedirs(VOICE_DIR, exist_ok=True)

# این‌ها رو از پروژه‌ی خودت import می‌کنیم -- امضاهای واقعی که پیدا کردیم:
#   transcribe(audio_path: str) -> str          (core/stt.py)
#   ask(question: str, agent: str = "hakim") -> str   (core/chat.py)
#   synthesize(text: str) -> str  (مسیر فایل صوتی خروجی)  (core/tts.py)
from core.stt import transcribe
from core.chat import ask
from core.tts import synthesize


@router.post("/voice")
async def receive_voice(request: Request):
    try:
        raw_pcm = await request.body()
        if len(raw_pcm) < 1000:
            raise HTTPException(status_code=400, detail="Voice data too small")

        ts = int(time.time())

        # صدای خام PCM 16-bit/16kHz/mono از ESP32 رو به یک فایل WAV واقعی تبدیل کن
        # (چون transcribe() احتمالاً یک فایل WAV سالم می‌خواد، نه PCM خام بی‌هدر)
        wav_path = os.path.join(VOICE_DIR, f"voice_{ts}.wav")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)      # 16-bit
            wf.setframerate(16000)
            wf.writeframes(raw_pcm)

        logger.info(f"Voice received: {len(raw_pcm)} bytes -> {wav_path}")

        # ۱. گفتار به متن
        user_text = transcribe(wav_path)
        logger.info(f"STT: {user_text}")

        if not user_text or not user_text.strip():
            raise HTTPException(status_code=422, detail="چیزی شنیده نشد")

        # ۲. گرفتن پاسخ از سیمرغ (پیش‌فرض پرسونای حکیم -- بعداً می‌شه پویا کرد)
        response_text = ask(user_text, agent="hakim")
        logger.info(f"Response: {response_text}")

        # ۳. متن به گفتار
        audio_out_path = synthesize(response_text)

        return FileResponse(
            audio_out_path,
            media_type="audio/wav",
            headers={
                "X-User-Text": user_text[:200],
                "X-Response-Text": response_text[:200],
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
