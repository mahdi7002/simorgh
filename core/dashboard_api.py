import sqlite3
from pathlib import Path

import psutil
from fastapi import APIRouter

from core.paths import LIBRARY_DB, POETRY_DB

router = APIRouter()
MAX_TEXT_QUERY = 200
MAX_PAGE_SIZE = 100


def _exists(path):
    return Path(path).exists()


def _safe_limit(value: int, default: int = 20) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, MAX_PAGE_SIZE))


def _safe_offset(value: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _safe_query(value: str) -> str:
    return (value or "").strip()[:MAX_TEXT_QUERY]


@router.get("/poets")
def list_poets():
    if not _exists(POETRY_DB):
        return []
    with sqlite3.connect(POETRY_DB) as conn:
        rows = conn.execute(
            "SELECT poet, COUNT(*) FROM poems_fts GROUP BY poet ORDER BY COUNT(*) DESC"
        ).fetchall()
    return [{"poet": r[0], "count": r[1]} for r in rows]


@router.get("/poet-poems")
def poet_poems(poet: str, limit: int = 50):
    if not _exists(POETRY_DB):
        return []
    poet = _safe_query(poet)
    limit = _safe_limit(limit, default=50)
    with sqlite3.connect(POETRY_DB) as conn:
        rows = conn.execute(
            "SELECT title, text FROM poems_fts WHERE poet = ? LIMIT ?",
            (poet, limit),
        ).fetchall()
    return [
        {
            "title": title or "بی‌عنوان",
            "snippet": " / ".join(
                s.strip() for s in (text or "").split("\n") if s.strip()
            )[:200],
        }
        for title, text in rows
    ]


@router.get("/library")
def library_list(limit: int = 100, offset: int = 0):
    limit = _safe_limit(limit, default=100)
    offset = _safe_offset(offset)
    if not _exists(LIBRARY_DB):
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}
    try:
        with sqlite3.connect(LIBRARY_DB) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM library WHERE status='done'"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT path,title,summary FROM library WHERE status='done' LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return {
            "items": [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows],
            "total": total,
        }
    except sqlite3.OperationalError:
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}


@router.get("/library-search")
def library_search(q: str, limit: int = 20):
    if not _exists(LIBRARY_DB):
        return []
    q = _safe_query(q)
    if not q:
        return []
    limit = _safe_limit(limit, default=20)
    try:
        with sqlite3.connect(LIBRARY_DB) as conn:
            rows = conn.execute(
                "SELECT path,title,summary FROM library_fts WHERE library_fts MATCH ? LIMIT ?",
                (q, limit),
            ).fetchall()
        return [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows]
    except sqlite3.OperationalError:
        return []


@router.get("/system-status")
def system_status():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }
