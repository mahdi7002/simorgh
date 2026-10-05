"""Deterministic knowledge fallback used when no local language model is available."""
from __future__ import annotations

import re
from typing import Any

from core.book_search import get_book_wisdom
from core.poetry_search import get_poetic_wisdom
from core.quran_search import get_quran_wisdom

_GREETINGS = {
    "سلام", "درود", "hi", "hello", "صبح بخیر", "عصر بخیر", "شب بخیر",
    "خداحافظ", "ممنون", "مرسی", "متشکرم", "تشکر", "سپاس", "چطوری",
    "حالت چطوره", "خوبی", "چه خبر", "هستی", "کسی هست",
}
_FILLER = {"سلام", "درود", "ممنون", "مرسی", "تشکر", "خوبی", "چطوری", "ببخشید", "لطفا", "لطفاً"}

SMALLTALK_REPLY = (
    "سلام! من سیمرغ هستم. چون الان مدل زبانی محلی در دسترس نیست، فقط می‌توانم "
    "از پایگاه دانش محلی (قرآن، شعر، کتاب‌ها) منبع پیدا کنم. یک موضوع یا کلیدواژه "
    "بپرس، مثلاً «صبر» یا «عدالت»."
)


def _normalize(text: str) -> str:
    text = text.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).strip().lower()


def is_smalltalk(query: str) -> bool:
    """True for greetings/thanks with no real topic, so we never retrieve noise."""
    norm = re.sub(r"\s+", " ", _normalize(query))
    if not norm:
        return True
    if norm in _GREETINGS:
        return True
    words = norm.split()
    return len(words) <= 4 and all(w in _FILLER or w in _GREETINGS for w in words)


def build_database_answer(query: str) -> tuple[str, list[dict[str, Any]]]:
    """Return a useful, provenance-labelled answer without invoking an LLM."""
    if is_smalltalk(query):
        return SMALLTALK_REPLY, []
    sources: list[dict[str, Any]] = []
    quran = get_quran_wisdom(query, limit=2)
    poetry = get_poetic_wisdom(query, limit=2)
    books = get_book_wisdom(query, limit=2)

    for item in quran:
        sources.append({"type": "quran", **item})
    for item in poetry:
        sources.append({"type": "poetry", **item})
    for item in books:
        sources.append({"type": "book", **item})

    if not sources:
        return (
            "مدل زبانی محلی در دسترس نیست. هستهٔ سیمرغ همچنان فعال است، "
            "اما برای این پرسش در پایگاه‌های دانش محلیِ نصب‌شده نتیجه‌ای پیدا نشد. "
            "این وضعیت به معنی خطا یا پاسخ جعلی نیست.",
            [],
        )

    lines = [
        "مدل زبانی محلی در دسترس نیست؛ این پاسخ مستقیماً از پایگاه دانش محلی سیمرغ ساخته شده است.",
    ]
    for source in sources:
        if source["type"] == "quran":
            ref = f"سوره {source.get('surah')}, آیه {source.get('ayah')}" if source.get("surah") else "قرآن"
            lines.append(f"[قرآن | {ref}] {source.get('text', '')}")
        elif source["type"] == "poetry":
            author = source.get("poet") or "شاعر نامشخص"
            title = source.get("title") or "بی‌عنوان"
            lines.append(f"[شعر | {author} | {title}] {source.get('snippet', '')}")
        else:
            lines.append(
                f"[کتاب | {source.get('doc_name', 'بی‌نام')}] {source.get('snippet', '')}"
            )
    lines.append("منبع بالا مستقیماً بازیابی شده است؛ تفسیر یا نتیجه‌گیری مدل زبانی در آن دخیل نیست.")
    return "\n".join(lines), sources


__all__ = ["build_database_answer", "is_smalltalk", "SMALLTALK_REPLY"]
