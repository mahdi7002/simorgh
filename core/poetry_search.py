# -*- coding: utf-8 -*-
"""Search the local Persian poetry database."""
import logging
import os
import re
import sqlite3
from contextlib import closing
from typing import Dict, List

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "simorgh_full.db")
STOPWORDS = {"من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با", "در", "و", "چیکار", "کنم"}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئ]+", text)
    return [w for w in words if w not in STOPWORDS and len(w) > 2][:max_words]


def get_poetic_wisdom(query: str, limit: int = 2) -> List[Dict]:
    if not os.path.exists(DB_PATH):
        return []
    keywords = _extract_keywords(query)
    if not keywords:
        return []
    match_query = " OR ".join(keywords)
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with conn:
                try:
                    rows = conn.execute(
                        "SELECT poet, title, text FROM poems_fts WHERE poems_fts MATCH ? ORDER BY rank LIMIT ?",
                        (match_query, limit),
                    ).fetchall()
                except Exception as exc:
                    logger.warning("FTS شعر شکست خورد، fallback LIKE: %s", exc)
                    like_clause = " OR ".join(["text LIKE ?" for _ in keywords])
                    params = [f"%{k}%" for k in keywords] + [limit]
                    rows = conn.execute(f"SELECT poet, title, text FROM poems WHERE {like_clause} LIMIT ?", params).fetchall()
    except Exception as exc:
        logger.warning("جستجوی شعر شکست خورد: %s", exc)
        return []
    results = []
    for poet, title, text in rows:
        lines = [s.strip() for s in text.strip().split("\n") if s.strip()]
        results.append({"poet": poet, "title": title or "", "snippet": " / ".join(lines[:2])[:200]})
    return results


def format_for_prompt(poems: List[Dict]) -> str:
    if not poems:
        return ""
    return "الهام از ادبیات فارسی:\n" + "\n".join(f'{p["poet"]}: «{p["snippet"]}»' for p in poems)
