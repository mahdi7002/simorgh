# -*- coding: utf-8 -*-
"""
core/poetry_search.py
جستجوی متنی در گنجینه‌ی اشعار فارسی (SimorghCore/data/simorgh.db)
از میان تمام شاعران (نه فقط یکی)، برای الهام‌گرفتن پاسخ‌های سیمرغ.
"""

import logging
import os
import re
import sqlite3
from typing import List, Dict

logger = logging.getLogger(__name__)

from core.paths import POETRY_DB as DB_PATH

STOPWORDS = {"من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با", "در", "و", "چیکار", "کنم"}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئ]+", text)
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return words[:max_words]


def get_poetic_wisdom(query: str, limit: int = 2) -> List[Dict]:
    """چند بیت مرتبط از میان همه‌ی شاعران برمی‌گردونه. اگه چیزی پیدا نشد، لیست خالی."""
    if not os.path.exists(DB_PATH):
        return []

    keywords = _extract_keywords(query)
    if not keywords:
        return []

    match_query = " OR ".join(keywords)

    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """
            SELECT poet, title, text
            FROM poems_fts
            WHERE poems_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match_query, limit),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"جستجوی شعر شکست خورد: {e}")
        return []

    results = []
    for poet, title, text in rows:
        lines = [s.strip() for s in text.strip().split("\n") if s.strip()]
        snippet = " / ".join(lines[:2])
        results.append({"poet": poet, "title": title or "", "snippet": snippet[:200]})
    return results


def format_for_prompt(poems: List[Dict]) -> str:
    """خروجی get_poetic_wisdom رو به یه متن کوتاه برای اضافه‌کردن به prompt تبدیل می‌کنه."""
    if not poems:
        return ""
    lines = [f'{p["poet"]}: «{p["snippet"]}»' for p in poems]
    return "الهام از ادبیات فارسی:\n" + "\n".join(lines)
