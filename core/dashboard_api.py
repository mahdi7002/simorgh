# -*- coding: utf-8 -*-
"""
core/dashboard_api.py
endpoint های کمکی برای داشبورد جدید: فهرست شاعران، اشعار هر شاعر،
و فهرست/جستجوی کتابخانهٔ اسناد (خروجی library_builder.py).
"""
import sqlite3
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

POETRY_DB = "/home/mahdi/SimorghCore/data/simorgh.db"
LIBRARY_DB = str(Path.home() / "simorgh" / "library_catalog.db")


@router.get("/poets")
def list_poets():
    conn = sqlite3.connect(POETRY_DB)
    rows = conn.execute(
        "SELECT poet, COUNT(*) as cnt FROM poems_fts GROUP BY poet ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [{"poet": r[0], "count": r[1]} for r in rows]


@router.get("/poet-poems")
def poet_poems(poet: str, limit: int = 50):
    conn = sqlite3.connect(POETRY_DB)
    rows = conn.execute(
        "SELECT title, text FROM poems_fts WHERE poet = ? LIMIT ?",
        (poet, limit)
    ).fetchall()
    conn.close()
    result = []
    for title, text in rows:
        lines = [s.strip() for s in text.strip().split("\n") if s.strip()]
        snippet = " / ".join(lines[:2])
        result.append({"title": title or "بی‌عنوان", "snippet": snippet[:200]})
    return result


@router.get("/library")
def library_list(limit: int = 100, offset: int = 0):
    if not Path(LIBRARY_DB).exists():
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}
    conn = sqlite3.connect(LIBRARY_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM library WHERE status='done'").fetchone()[0]
        rows = conn.execute(
            "SELECT path, title, summary FROM library WHERE status='done' LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return {"items": [], "total": 0, "note": "کتابخانه هنوز در حال ساخته‌شدن است."}
    conn.close()
    return {
        "items": [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows],
        "total": total,
    }


@router.get("/library-search")
def library_search(q: str, limit: int = 20):
    if not Path(LIBRARY_DB).exists():
        return []
    conn = sqlite3.connect(LIBRARY_DB)
    try:
        rows = conn.execute(
            "SELECT path, title, summary FROM library_fts WHERE library_fts MATCH ? LIMIT ?",
            (q, limit)
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()
    return [{"path": r[0], "title": r[1], "summary": r[2]} for r in rows]


@router.get("/system-status")
def system_status():
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }
