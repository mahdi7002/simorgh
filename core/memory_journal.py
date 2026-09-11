import sqlite3
from datetime import datetime
from core.paths import JOURNAL_DB

def _init_db():
    JOURNAL_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(JOURNAL_DB)
    conn.execute("CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, place TEXT, note TEXT)")
    conn.commit()
    return conn

def add_entry(place: str, note: str) -> int:
    conn = _init_db()
    cur = conn.execute("INSERT INTO journal_entries(timestamp, place, note) VALUES (?, ?, ?)", (datetime.now().isoformat(timespec="seconds"), place, note))
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id

def get_entries(limit: int = 20) -> list:
    conn = _init_db()
    rows = conn.execute("SELECT timestamp, place, note FROM journal_entries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]

def search_entries(query: str) -> list:
    conn = _init_db()
    rows = conn.execute("SELECT timestamp, place, note FROM journal_entries WHERE place LIKE ? OR note LIKE ?", (f"%{query}%", f"%{query}%")).fetchall()
    conn.close()
    return [{"timestamp": r[0], "place": r[1], "note": r[2]} for r in rows]
