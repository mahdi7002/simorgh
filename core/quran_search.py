# -*- coding: utf-8 -*-
"""
core/quran_search.py
جستجوی متنی در ترجمه‌ی قرآن — با تمرکز بر دقت (نه صرفاً یافتن هر نتیجه‌ای).
"""
import logging
import os
import re
import sqlite3
from typing import List, Dict

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "grid", "quran.db")

# کلمات عمومی/فعل‌های رایج که در اکثر آیات ظاهر می‌شوند و باعث نویز می‌شوند
STOPWORDS = {
    "من", "تو", "او", "ما", "شما", "این", "که", "را", "به", "از", "با",
    "در", "و", "چیکار", "کنم", "بگو", "است", "شد", "کرد", "هست", "بود",
    "کن", "شود", "برای", "همه", "هیچ", "قصه", "داستان",
}


def _extract_keywords(text: str, max_words: int = 5) -> List[str]:
    words = re.findall(r"[آ-یءئ]+", text)
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return words[:max_words]


def get_quran_wisdom(query: str, limit: int = 3) -> List[Dict]:
    """فقط وقتی کلیدواژهٔ معنادار (غیر از فعل‌های عمومی) پیدا شد، جستجو می‌کند."""
    if not os.path.exists(DB_PATH):
        return []

    keywords = _extract_keywords(query)
    if not keywords:
        return []  # اگر فقط کلمات عمومی بود، اصلاً وارد قرآن نشو

    # AND به‌جای OR: دقت بالاتر، حتی اگر نتیجه کمتر شود
    match_query = " AND ".join(keywords)

    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """
            SELECT category, content
            FROM knowledge_fts
            WHERE knowledge_fts MATCH ? AND category = 'معنوی'
            ORDER BY rank
            LIMIT ?
            """,
            (match_query, limit),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"جستجوی قرآن شکست خورد یا نتیجه‌ای نداشت: {e}")
        return []

    results = []
    for category, content in rows:
        m = re.match(r"سوره\s*(\d+)\s*آیه\s*(\d+)\s*\|\s*(.*)", content.strip())
        if m:
            results.append({"surah": m.group(1), "ayah": m.group(2), "text": m.group(3).strip()})
        else:
            results.append({"surah": "", "ayah": "", "text": content.strip()[:200]})
    return results


def format_for_prompt(verses: List[Dict]) -> str:
    if not verses:
        return ""
    lines = []
    for v in verses:
        tag = f"(سوره {v['surah']}, آیه {v['ayah']})" if v["surah"] else ""
        lines.append(f"«{v['text']}» {tag}".strip())
    return "الهام از قرآن:\n" + "\n".join(lines)
