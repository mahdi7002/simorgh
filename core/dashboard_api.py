import sqlite3
import psutil
from pathlib import Path
from fastapi import APIRouter
from core.paths import POETRY_DB, LIBRARY_DB

router = APIRouter()

def _exists(path):
    return Path(path).exists()

@router.get("/poets")
def list_poets():
    if not _exists(POETRY_DB): return []
    with sqlite3.connect(POETRY_DB) as conn:
        rows = conn.execute("SELECT poet, COUNT(*) FROM poems_fts GROUP BY poet ORDER BY COUNT(*) DESC").fetchall()
    return [{"poet": r[0], "count": r[1]} for r in rows]

@router.get("/poet-poems")
def poet_poems(poet: str, limit: int = 50):
    if not _exists(POETRY_DB): return []
    with sqlite3.connect(POETRY_DB) as conn:
        rows = conn.execute("SELECT title, text FROM poems_fts WHERE poet = ? LIMIT ?", (poet, limit)).fetchall()
    return [{"title": title or "بی‌عنوان", "snippet": " / ".join(s.strip() for s in (text or "").split("\n") if s.strip())[:200]} for title, text in rows]

@router.get("/library")
def library_list(limit: int = 100, offset: int = 0):
    if not _exists(LIBRARY_DB):
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}
    try:
        with sqlite3.connect(LIBRARY_DB) as conn:
            total = conn.execute("SELECT COUNT(*) FROM library WHERE status='done'").fetchone()[0]
            rows = conn.execute("SELECT path,title,summary FROM library WHERE status='done' LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return {"items": [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows], "total": total}
    except sqlite3.OperationalError:
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}

@router.get("/library-search")
def library_search(q: str, limit: int = 20):
    if not _exists(LIBRARY_DB): return []
    try:
        with sqlite3.connect(LIBRARY_DB) as conn:
            rows = conn.execute("SELECT path,title,summary FROM library_fts WHERE library_fts MATCH ? LIMIT ?", (q, limit)).fetchall()
        return [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows]
    except sqlite3.OperationalError:
        return []

@router.get("/system-status")
def system_status():
    return {"cpu_percent": psutil.cpu_percent(interval=0.1), "ram_percent": psutil.virtual_memory().percent, "disk_percent": psutil.disk_usage("/").percent}
