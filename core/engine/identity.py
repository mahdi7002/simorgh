import sqlite3, json, os, datetime, platform
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def get_self_model():
    conn = sqlite3.connect(DB_PATH)
    reqs = conn.execute("SELECT COUNT(*) FROM request_log").fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM request_log WHERE response_time_ms < 0").fetchone()[0]
    version = "2.2 (Living System)"
    host = platform.node()
    return {
        "name": "Simorgh",
        "version": version,
        "host": host,
        "total_requests": reqs,
        "state": "evolving",
        "philosophy": "Understanding over answering."
    }

def respond_to_criticism(criticism_text):
    return f"من متوجه نقد شما هستم: '{criticism_text}'. من یک سیستم در حال یادگیری هستم و این بازخورد را برای بهبود ثبت می‌کنم. ممنون از کمک شما."
