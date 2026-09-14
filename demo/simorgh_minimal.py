#!/usr/bin/env python3
"""
SIMORGH minimal demo

This is intentionally a tiny, dependency-free connectivity demo, not a
replacement for the full SIMORGH runtime.

Behavior:
  1. If a local OpenAI-compatible LLM endpoint is reachable, ask the local
     model through the Hakim persona.
  2. If no local model is reachable, report that the model is unavailable.
     The demo never fabricates an answer merely to make the test look alive.

That distinction is deliberate: model-unavailable is a real runtime state,
not a reason to invent an unrelated answer.

Usage:
    python3 demo/simorgh_minimal.py --test
    python3 demo/simorgh_minimal.py "پرسش شما اینجا"
    python3 demo/simorgh_minimal.py

Environment variables:
    SIMORGH_LLM_URL   default: http://127.0.0.1:8080/v1/chat/completions
    SIMORGH_TIMEOUT   default: 3 seconds
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

LLM_URL = os.environ.get(
    "SIMORGH_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions"
)
TIMEOUT = float(os.environ.get("SIMORGH_TIMEOUT", "3"))

HAKIM_SYSTEM_PROMPT = (
    "تو حکیم هستی، یکی از پرسونای سیمرغ. با آرامش، دقت و صداقت پاسخ می‌دهی. "
    "اگر شواهد یا اطلاعات کافی نداری، صریح بگو که نمی‌دانی."
)

MODEL_UNAVAILABLE = (
    "[MODEL UNAVAILABLE] مدل زبانی محلی در دسترس نیست. "
    "هیچ پاسخ ساختگی یا جایگزین نامرتبط تولید نشد. "
    "برای اجرای پاسخ واقعی، یک endpoint محلی OpenAI-compatible را روی "
    f"{LLM_URL} اجرا کنید."
)


def call_local_llm(question: str) -> str | None:
    """Call the local model. Return None when the model is unavailable."""
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": HAKIM_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "max_tokens": 200,
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
            content = data["choices"][0]["message"]["content"]
            answer = str(content).strip()
            return answer or None
    except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError, OSError):
        return None


def ask(question: str) -> tuple[str, str]:
    """Return (answer, mode) without inventing a fallback answer."""
    answer = call_local_llm(question)
    if answer:
        return answer, "llm"
    return MODEL_UNAVAILABLE, "unavailable"


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] == "--test":
        answer, mode = ask("زندگی چیست؟")
        ok = bool(answer.strip()) and mode in {"llm", "unavailable"}
        print(f"[mode={mode}] {answer}")
        print("TEST PASS" if ok else "TEST FAIL")
        sys.exit(0 if ok else 1)

    if args:
        question = " ".join(args).strip()
        answer, mode = ask(question)
        print(f"[{mode}] {answer}")
        return

    print("سیمرغ | نمونه‌ی مینیمال | حکیم")
    print(f"مدل محلی: {LLM_URL}")
    print("در صورت نبود مدل، سیمرغ پاسخ ساختگی تولید نمی‌کند. برای خروج: Ctrl+C\n")

    while True:
        try:
            question = input("شما: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخداحافظ.")
            break
        if not question:
            continue
        answer, mode = ask(question)
        print(f"حکیم [{mode}]: {answer}\n")


if __name__ == "__main__":
    main()
