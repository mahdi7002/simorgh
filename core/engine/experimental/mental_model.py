import sqlite3, json, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def update_user_profile(user_id="mahdi"):
    conn = sqlite3.connect(DB_PATH)
    intents = conn.execute("SELECT intent, COUNT(*) FROM request_log WHERE intent NOT NULL GROUP BY intent ORDER BY COUNT(*) DESC LIMIT 5").fetchall()
    hours = conn.execute("SELECT strftime('%H', timestamp) as hour, COUNT(*) FROM request_log GROUP BY hour ORDER BY COUNT(*) DESC LIMIT 3").fetchall()
    profile = {
        "user_id": user_id,
        "top_intents": [{"intent": r[0], "count": r[1]} for r in intents],
        "active_hours": [{"hour": r[0], "count": r[1]} for r in hours],
        "last_updated": datetime.now().isoformat()
    }
    conn.execute("INSERT OR REPLACE INTO personal_memory (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                 (f"profile_{user_id}", json.dumps(profile, ensure_ascii=False)))
    conn.commit()
    conn.close()
    return profile

def get_user_profile(user_id="mahdi"):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT value FROM personal_memory WHERE key=?", (f"profile_{user_id}",)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None
