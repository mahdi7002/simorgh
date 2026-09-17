# -*- coding: utf-8 -*-
"""Search the local Quran translation database."""
import logging
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "grid" / "quran.db"
DB_PATH = Path(os.environ.get("SIMORGH_QURAN_DB", str(DEFAULT_DB_PATH))).expanduser().resolve()
STOPWORDS = {"من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با", "در", "و", "چیکار", "کنم", "بگو", "است", "شد", "کرد", "هست", "بود", "کن", "شود", "برای", "همه", "هیچ", "قصه", "داستان"}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئ]+", text)
    return [w for w in words if w not in STOPWORDS and len(w) > 2][:max_words]


def get_quran_wisdom(query: str, limit: int = 3) -> List[Dict]:
    if not DB_PATH.is_file():
        return []
    keywords = _extract_keywords(query)
    if not keywords:
        return []
    match_query = " AND ".join(keywords)
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with conn:
                rows = conn.execute(
                    "SELECT category, content FROM knowledge_fts WHERE knowledge_fts MATCH ? AND category = 'معنوی' ORDER BY rank LIMIT ?",
                    (match_query, limit),
                ).fetchall()
    except Exception as exc:
        logger.warning("جستجوی قرآن شکست خورد: %s", exc)
        return []
    results = []
    for _category, content in rows:
        match = re.match(r"سوره\s*(\d+)\s*آیه\s*(\d+)\s*\|\s*(.*)", content.strip())
        if match:
            results.append({"surah": match.group(1), "ayah": match.group(2), "text": match.group(3).strip()})
        else:
            results.append({"surah": "", "ayah": "", "text": content.strip()[:200]})
    return results


def format_for_prompt(verses: List[Dict]) -> str:
    if not verses:
        return ""
    lines = []
    for verse in verses:
        tag = f"(سوره {verse['surah']}, آیه {verse['ayah']})" if verse["surah"] else ""
        lines.append(f"«{verse['text']}» {tag}".strip())
    return "الهام از قرآن:\n" + "\n".join(lines)
