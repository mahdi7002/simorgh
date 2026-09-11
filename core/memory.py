import json
import sqlite3
from core.paths import MEMORY_DB

class MemoryEngine:
    def __init__(self, db_path=None):
        self.db_path = MEMORY_DB if db_path is None else db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, user_input TEXT, system_response TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, metadata JSON)")
            conn.execute("CREATE TABLE IF NOT EXISTS user_profile (id INTEGER PRIMARY KEY, preferences JSON, projects JSON, recurring_goals JSON, last_updated DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def store_conversation(self, session_id, user_input, system_response, metadata=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO conversations(session_id,user_input,system_response,metadata) VALUES(?,?,?,?)", (session_id,user_input,system_response,json.dumps(metadata, ensure_ascii=False) if metadata else None))

    def get_conversation_history(self, session_id, limit=10):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT user_input,system_response,timestamp FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id,limit)).fetchall()
        return [{"user":r[0],"system":r[1],"time":r[2]} for r in rows]
