# -*- coding: utf-8 -*-
"""
core/book_search.py
جستجو در تکه‌های کتاب‌های PDF ایمپورت‌شده، برای استفاده در جواب‌های سیمرغ.
"""

import logging
import os
import re
import sqlite3
from typing import List, Dict

logger = logging.getLogger(__name__)

DB_PATH = "/home/mahdi/SimorghCore/data/simorgh.db"
STOPWORDS = {"من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با", "در", "و"}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئA-Za-z]+", text)
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return words[:max_words]


def get_book_wisdom(query: str, limit: int = 2) -> List[Dict]:
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
            SELECT doc_name, category, chunk_text
            FROM book_chunks_fts
            WHERE book_chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match_query, limit),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"جستجوی کتاب شکست خورد: {e}")
        return []

    return [{"doc_name": r[0], "category": r[1], "snippet": r[2][:300]} for r in rows]


def format_for_prompt(chunks: List[Dict]) -> str:
    if not chunks:
        return ""
    lines = [f'از کتاب «{c["doc_name"]}»: {c["snippet"]}' for c in chunks]
    return "الهام از کتاب‌ها:\n" + "\n".join(lines)
