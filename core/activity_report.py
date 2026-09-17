# -*- coding: utf-8 -*-
"""Render the local activity log as a human-readable Persian report."""
import sqlite3
from contextlib import closing
from datetime import datetime

try:
    from core.paths import ACTIVITY_DB
    DB_PATH = str(ACTIVITY_DB)
except Exception:
    from pathlib import Path
    DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "activity.db")
POLL_SECONDS = 15


def get_daily_report(date_str: str = None) -> str:
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            rows = conn.execute(
                "SELECT app, window_title, timestamp FROM activity_log WHERE timestamp LIKE ? ORDER BY timestamp",
                (f"{date_str}%",),
            ).fetchall()
    if not rows:
        return f"برای {date_str} هیچ فعالیتی ثبت نشده."
    app_seconds = {}
    for app, _title, _timestamp in rows:
        app_seconds[app] = app_seconds.get(app, 0) + POLL_SECONDS
    total_seconds = sum(app_seconds.values())
    sorted_apps = sorted(app_seconds.items(), key=lambda item: -item[1])
    lines = [f"📊 گزارش فعالیت {date_str}", f"مجموع زمان ثبت‌شده: {_fmt(total_seconds)}", ""]
    for app, secs in sorted_apps:
        pct = (secs / total_seconds * 100) if total_seconds else 0
        lines.append(f"- {app}: {_fmt(secs)} ({pct:.0f}%)")
    return "\n".join(lines)


def _fmt(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} ساعت و {minutes} دقیقه" if hours else f"{minutes} دقیقه"


if __name__ == "__main__":
    print(get_daily_report())
