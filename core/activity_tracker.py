# -*- coding: utf-8 -*-
"""Optional desktop activity tracker using X11 and a local SQLite database."""
import os
from contextlib import closing
from datetime import datetime
from pathlib import Path
import re
import sqlite3
import subprocess
import time

try:
    from core.paths import ACTIVITY_DB
    DB_PATH = str(ACTIVITY_DB)
except Exception:
    DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "activity.db")
POLL_SECONDS = 15


def _connect():
    return closing(sqlite3.connect(DB_PATH))


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _connect() as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    app TEXT,
                    window_title TEXT
                )
            """)


def get_active_window():
    try:
        out = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True, timeout=3).stdout
        match = re.search(r"# (0x[0-9a-fA-F]+)", out)
        if not match:
            return None, None
        win_id = match.group(1)
        info = subprocess.run(["xprop", "-id", win_id, "WM_CLASS", "_NET_WM_NAME"], capture_output=True, text=True, timeout=3).stdout
        cls_match = re.search(r'WM_CLASS\(STRING\) = "[^"]*", "([^"]*)"', info)
        title_match = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', info)
        return (cls_match.group(1) if cls_match else None, title_match.group(1) if title_match else None)
    except Exception:
        return None, None


def main():
    init_db()
    print("ردیاب فعالیت سیمرغ شروع شد.")
    while True:
        app, title = get_active_window()
        if app:
            with _connect() as conn:
                with conn:
                    conn.execute(
                        "INSERT INTO activity_log (timestamp, app, window_title) VALUES (?, ?, ?)",
                        (datetime.now().isoformat(), app, title or ""),
                    )
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
