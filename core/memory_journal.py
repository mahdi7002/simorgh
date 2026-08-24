# -*- coding: utf-8 -*-
"""
core/memory_journal.py
دفتر خاطرات مکانی ساده — الهام‌گرفته از مفهوم «کتاب خاطرات متصل به مکان»
در سند طیّبه، بدون نیاز به NFC/بلاک‌چین/گردنبند فیزیکی. فقط SQLite.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = str(Path.home() / "simorgh" / "journal.db")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            place TEXT,
            note TEXT
        )
    """)
    conn.commit()
    return conn


def add_entry(place: str, note: str) -> int:
    conn = _init_db()
    ts = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO journal_entries(timestamp, place, note) VALUES (?, ?, ?)",
        (ts, place, note)
    )
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id


def get_entries(limit: int = 20) -> list:
    conn = _init_db()
    rows = conn.execute(
        "SELECT timestamp, place, note FROM journal_entries ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]


def search_entries(query: str) -> list:
    conn = _init_db()
    rows = conn.execute(
        "SELECT timestamp, place, note FROM journal_entries WHERE place LIKE ? OR note LIKE ?",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]
