# -*- coding: utf-8 -*-
"""Search imported book chunks in the local SQLite knowledge store."""
import logging
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "simorgh_full.db"
DB_PATH = Path(os.environ.get("SIMORGH_BOOKS_DB", str(DEFAULT_DB_PATH))).expanduser().resolve()
STOPWORDS = {"من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با", "در", "و"}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئA-Za-z]+", text)
    return [w for w in words if w not in STOPWORDS and len(w) > 2][:max_words]


def get_book_wisdom(query: str, limit: int = 2) -> List[Dict]:
    if not DB_PATH.is_file():
        return []
    keywords = _extract_keywords(query)
    if not keywords:
        return []
    match_query = " OR ".join(keywords)
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with conn:
                rows = conn.execute(
                    "SELECT doc_name, category, chunk_text FROM book_chunks_fts WHERE book_chunks_fts MATCH ? ORDER BY rank LIMIT ?",
                    (match_query, limit),
                ).fetchall()
    except Exception as exc:
        logger.warning("جستجوی کتاب شکست خورد: %s", exc)
        return []
    return [{"doc_name": row[0], "category": row[1], "snippet": row[2][:300]} for row in rows]


def format_for_prompt(chunks: List[Dict]) -> str:
    if not chunks:
        return ""
    return "الهام از کتاب‌ها:\n" + "\n".join(f'از کتاب «{c["doc_name"]}»: {c["snippet"]}' for c in chunks)
