# -*- coding: utf-8 -*-
"""
core/activity_tracker.py
هر ۱۵ ثانیه پنجره‌ی فعال روی دسکتاپ رو (با xprop، بدون نیاز به نصب چیز جدید) می‌خونه
و توی یه دیتابیس سبک ذخیره می‌کنه. جدا از سرویس اصلی سیمرغ اجرا می‌شه چون به
نشست گرافیکی (X11) نیاز داره.
"""

import os
import re
import sqlite3
import subprocess
import time
from datetime import datetime

DB_PATH = "/home/mahdi/SimorghCore/data/activity.db"
POLL_SECONDS = 15


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            app TEXT,
            window_title TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_active_window():
    """برمی‌گردونه (app_class, window_title) یا (None, None) اگه نشد بخونه."""
    try:
        out = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True, text=True, timeout=3
        ).stdout
        m = re.search(r"# (0x[0-9a-fA-F]+)", out)
        if not m:
            return None, None
        win_id = m.group(1)

        info = subprocess.run(
            ["xprop", "-id", win_id, "WM_CLASS", "_NET_WM_NAME"],
            capture_output=True, text=True, timeout=3
        ).stdout

        app = None
        title = None
        cls_match = re.search(r'WM_CLASS\(STRING\) = "[^"]*", "([^"]*)"', info)
        if cls_match:
            app = cls_match.group(1)
        title_match = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "([^"]*)"', info)
        if title_match:
            title = title_match.group(1)
        return app, title
    except Exception:
        return None, None


def main():
    init_db()
    print("ردیاب فعالیت سیمرغ شروع شد.")
    while True:
        app, title = get_active_window()
        if app:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO activity_log (timestamp, app, window_title) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), app, title or ""),
            )
            conn.commit()
            conn.close()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
