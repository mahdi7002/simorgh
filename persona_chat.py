"""
persona_chat.py — موتور گفت‌وگوی زنده‌ی ۱۲ پرسونا
====================================================
هر پرسونا یک سیستم‌پرامپت واقعی است که به یک مدل زبانی محلی (llama-server
یا هر endpoint سازگار با OpenAI) وصل می‌شود. اگر سرور محلی در دسترس نبود،
به‌جای خطا یا سکوت، به یک حالت آفلوقی صادقانه برمی‌گردد — دقیقاً همان
اصل «تخریب تدریجی، نه شکست کامل» که در سراسر سیمرغ رعایت شده.

استفاده (بعد از قرار گرفتن در پروژه):
    from fastapi import FastAPI
    from persona_chat import router as persona_router
    app.include_router(persona_router)

اجرای مستقل برای تست سریع:
    python3 persona_chat.py --test
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from personas import get_persona, list_personas

LLM_URL = os.environ.get("SIMORGH_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
# روی این سخت‌افزار (CPU-only, بدون کارت گرافیک) هر توکن ~۱۲۰ میلی‌ثانیه
# طول می‌کشد — یعنی یک پاسخ ۳۰۰ توکنی می‌تواند تا ۴۰-۵۰ ثانیه طول بکشد.
# timeout باید این واقعیت را در نظر بگیرد، وگرنه بی‌صدا به حالت آفلاین
# سقوط می‌کند در حالی که مدل داشت جواب درست تولید می‌کرد.
TIMEOUT = float(os.environ.get("SIMORGH_TIMEOUT", "90"))
MAX_TOKENS = int(os.environ.get("SIMORGH_MAX_TOKENS", "300"))


def call_local_llm(system_prompt: str, message: str) -> str | None:
    """Call the local OpenAI-compatible LLM endpoint. Returns None on any
    failure — this must never raise, so callers can fall back gracefully."""
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "max_tokens": MAX_TOKENS,
    }
    try:
        req = urllib.request.Request(
            LLM_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, OSError):
        return None


def chat_with_persona(persona_id: str, message: str) -> dict:
    """Core logic, usable with or without FastAPI installed."""
    persona = get_persona(persona_id)
    if persona is None:
        return {
            "error": f"پرسونای «{persona_id}» یافت نشد.",
            "available": [p["id"] for p in list_personas()],
        }

    answer = call_local_llm(persona.full_prompt, message)
    if answer is not None:
        return {
            "persona": persona.id,
            "persona_name": persona.name_fa,
            "mode": "llm",
            "answer": answer,
        }

    # Graceful offline fallback — never a hard failure.
    return {
        "persona": persona.id,
        "persona_name": persona.name_fa,
        "mode": "offline",
        "answer": (
            f"[{persona.name_fa}] سرور مدل محلی در دسترس نیست "
            f"({LLM_URL}). این پرسونا معمولاً درباره‌ی «{persona.role_fa}» "
            "کمک می‌کند — llama-server را روشن کن تا پاسخ زنده بگیری."
        ),
    }


# ---------------------------------------------------------------------------
# FastAPI wiring (only active if fastapi is installed in this environment)
# ---------------------------------------------------------------------------
if HAS_FASTAPI:
    router = APIRouter(prefix="/persona", tags=["personas"])

    class ChatRequest(BaseModel):
        message: str

    @router.get("/list")
    def api_list_personas():
        return {"personas": list_personas()}

    @router.post("/{persona_id}/chat")
    def api_chat(persona_id: str, req: ChatRequest):
        result = chat_with_persona(persona_id, req.message)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result)
        return result


# ---------------------------------------------------------------------------
# Standalone test entry point — works with zero setup, no FastAPI required.
# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]

    if args and args[0] == "--test":
        all_personas = list_personas()
        ok = len(all_personas) == 12
        print(f"شمار پرسوناها: {len(all_personas)} (باید ۱۲ باشد)")
        for p in all_personas:
            print(f"  - {p['id']:10} {p['name_fa']:8} {p['role_fa']}")

        print()
        result = chat_with_persona("hakim", "زندگی چیست؟")
        print(f"[نمونه پاسخ حکیم — mode={result['mode']}]")
        print(result["answer"])

        print()
        print("TEST PASS" if ok and "answer" in result else "TEST FAIL")
        sys.exit(0 if ok else 1)

    if len(args) >= 2:
        persona_id, message = args[0], " ".join(args[1:])
        result = chat_with_persona(persona_id, message)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("استفاده: python3 persona_chat.py <persona_id> <پیام>")
    print("یا: python3 persona_chat.py --test")
    print("\nپرسوناهای موجود:")
    for p in list_personas():
        print(f"  {p['id']:10} {p['name_fa']}")


if __name__ == "__main__":
    main()
