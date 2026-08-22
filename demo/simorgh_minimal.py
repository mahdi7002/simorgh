#!/usr/bin/env python3
"""
Simorgh — Minimal Demo
=======================
A single-file, dependency-free demonstration of the Simorgh persona
architecture. This is intentionally NOT the full system (no 1M-verse
poetry index, no 38k-entry Quran database, no whisper.cpp) — it exists
so that anyone cloning this repository has something that runs
immediately, with zero setup, on any machine with Python 3.8+.

Behavior:
  1. If a local LLM server is reachable (llama-server / any OpenAI-
     compatible endpoint at SIMORGH_LLM_URL), it is used for real
     generation through the "hakim" (sage) persona system prompt.
  2. If no server is reachable, it falls back to a small offline
     wisdom-retrieval mode using a handful of public-domain classical
     Persian couplets (Hafez, Rumi, Saadi — all in the public domain).

This fallback guarantees the demo ALWAYS produces a working, on-topic
response — never a crash, never a blank screen — which mirrors a core
design principle of the full Simorgh system: local-first, zero
required API keys, graceful degradation instead of hard failure.

Usage:
    python3 simorgh_minimal.py                 # interactive loop
    python3 simorgh_minimal.py --test           # single automated check, exits 0/1
    python3 simorgh_minimal.py "پرسش شما اینجا"  # single one-shot query

Env vars (all optional):
    SIMORGH_LLM_URL   default: http://127.0.0.1:8080/v1/chat/completions
    SIMORGH_TIMEOUT   default: 3 (seconds)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

LLM_URL = os.environ.get("SIMORGH_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")
TIMEOUT = float(os.environ.get("SIMORGH_TIMEOUT", "3"))

HAKIM_SYSTEM_PROMPT = (
    "تو حکیم هستی، یکی از پرسونای سیمرغ. با آرامش، دقت، و ریشه در ادبیات "
    "کلاسیک فارسی پاسخ می‌دهی. پاسخ‌ها کوتاه، صادقانه و بدون اغراق‌اند."
)

# A small, offline, public-domain wisdom set for the no-server fallback.
# Full couplets are safe to include verbatim: these poets (Hafez d.1390,
# Rumi d.1273, Saadi d.1291) have been in the public domain for centuries.
WISDOM = [
    {
        "keywords": ["عدالت", "انصاف", "حق"],
        "poet": "سعدی",
        "verse": "بنی‌آدم اعضای یکدیگرند / که در آفرینش ز یک گوهرند",
    },
    {
        "keywords": ["عشق", "دل", "دوست"],
        "poet": "مولانا",
        "verse": "هر کسی کو دور ماند از اصل خویش / باز جوید روزگار وصل خویش",
    },
    {
        "keywords": ["صبر", "سختی", "غم", "رنج"],
        "poet": "حافظ",
        "verse": "غم زمانه که هیچش کران نمی‌بینم / دوای آن به جز از می ندانم ای ساقی",
    },
    {
        "keywords": ["دانش", "علم", "آموختن"],
        "poet": "سعدی",
        "verse": "چو نیکو نظر کرد صاحب‌بصر / به از علم دیدی نیامد دگر",
    },
    {
        "keywords": ["زندگی", "دنیا", "روزگار"],
        "poet": "خیام",
        "verse": "این قافله‌ی عمر عجب می‌گذرد / دریاب دمی که با طرب می‌گذرد",
    },
]

DEFAULT_WISDOM = {
    "poet": "حافظ",
    "verse": "بیا تا گل برافشانیم و می در ساغر اندازیم / فلک را سقف بشکافیم و طرحی نو دراندازیم",
}


def call_local_llm(question: str) -> str | None:
    """Try a local OpenAI-compatible endpoint. Returns None on any failure
    so the caller can fall back — this must never raise."""
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
            return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, OSError):
        return None


def offline_wisdom(question: str) -> str:
    """Deterministic offline fallback: keyword-match against a tiny
    embedded public-domain wisdom set. Always returns something."""
    for entry in WISDOM:
        if any(kw in question for kw in entry["keywords"]):
            return f"{entry['verse']}\n— {entry['poet']}"
    return f"{DEFAULT_WISDOM['verse']}\n— {DEFAULT_WISDOM['poet']}"


def ask(question: str) -> tuple[str, str]:
    """Returns (answer, mode) where mode is 'llm' or 'offline'."""
    answer = call_local_llm(question)
    if answer:
        return answer, "llm"
    return offline_wisdom(question), "offline"


def main():
    args = sys.argv[1:]

    if args and args[0] == "--test":
        answer, mode = ask("زندگی چیست؟")
        ok = bool(answer and len(answer.strip()) > 0)
        print(f"[mode={mode}] {answer}")
        print("TEST PASS" if ok else "TEST FAIL")
        sys.exit(0 if ok else 1)

    if args:
        question = " ".join(args)
        answer, mode = ask(question)
        print(f"[{mode}] {answer}")
        return

    print("سیمرغ — نمونه‌ی مینیمال (حکیم). برای خروج: Ctrl+C")
    print(f"(اتصال به سرور محلی: {LLM_URL} — در صورت نبود سرور، حالت آفلاین فعال می‌شود)\n")
    while True:
        try:
            question = input("شما: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخداحافظ.")
            break
        if not question:
            continue
        answer, mode = ask(question)
        tag = "زنده" if mode == "llm" else "آفلاین"
        print(f"حکیم [{tag}]: {answer}\n")


if __name__ == "__main__":
    main()
