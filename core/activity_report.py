# -*- coding: utf-8 -*-
"""
core/activity_report.py
لاگ خام فعالیت رو به یه گزارش خوانا و فارسی تبدیل می‌کنه: امروز چقدر روی چی کار کردی.
"""

import sqlite3
from datetime import datetime

try:
    from core.paths import ACTIVITY_DB
    DB_PATH = str(ACTIVITY_DB)
except Exception:
    from pathlib import Path
    DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "activity.db")
POLL_SECONDS = 15  # باید با activity_tracker.py هماهنگ باشه


def get_daily_report(date_str: str = None) -> str:
    """date_str مثل '2026-07-11'؛ اگه ندی، امروز رو حساب می‌کنه."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT app, window_title, timestamp FROM activity_log WHERE timestamp LIKE ? ORDER BY timestamp",
        (f"{date_str}%",),
    ).fetchall()
    conn.close()

    if not rows:
        return f"برای {date_str} هیچ فعالیتی ثبت نشده."

    app_seconds = {}
    for app, title, ts in rows:
        app_seconds[app] = app_seconds.get(app, 0) + POLL_SECONDS

    total_seconds = sum(app_seconds.values())
    sorted_apps = sorted(app_seconds.items(), key=lambda x: -x[1])

    lines = [f"📊 گزارش فعالیت {date_str}", f"مجموع زمان ثبت‌شده: {_fmt(total_seconds)}", ""]
    for app, secs in sorted_apps:
        pct = (secs / total_seconds * 100) if total_seconds else 0
        lines.append(f"- {app}: {_fmt(secs)} ({pct:.0f}%)")

    return "\n".join(lines)


def _fmt(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h:
        return f"{h} ساعت و {m} دقیقه"
    return f"{m} دقیقه"


if __name__ == "__main__":
    print(get_daily_report())
