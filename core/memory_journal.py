import sqlite3
from contextlib import closing
from datetime import datetime
from core.paths import JOURNAL_DB


def _connect():
    return closing(sqlite3.connect(JOURNAL_DB))


def _init_db():
    JOURNAL_DB.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, place TEXT, note TEXT)"
            )


def add_entry(place: str, note: str) -> int:
    _init_db()
    with _connect() as conn:
        with conn:
            cur = conn.execute(
                "INSERT INTO journal_entries(timestamp, place, note) VALUES (?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), place, note),
            )
            return int(cur.lastrowid)


def get_entries(limit: int = 20) -> list:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, place, note FROM journal_entries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]


def search_entries(query: str) -> list:
    _init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, place, note FROM journal_entries WHERE place LIKE ? OR note LIKE ?",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]
