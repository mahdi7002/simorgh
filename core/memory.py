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

    def _ensure_provenance_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS provenance_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL, source TEXT NOT NULL,
                confidence REAL DEFAULT 0.5, tags TEXT,
                status TEXT DEFAULT 'KNOWN',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

    def store_with_provenance(self, content, source, confidence=0.5, tags=None, status="KNOWN"):
        self._ensure_provenance_table()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO provenance_memory(content,source,confidence,tags,status) VALUES(?,?,?,?,?)",
                (content, source, float(confidence), __import__('json').dumps(tags or [], ensure_ascii=False), status))

    def search_with_provenance(self, query, limit=10):
        self._ensure_provenance_table()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT content,source,confidence,status,created_at FROM provenance_memory WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit)).fetchall()
        if not rows:
            return [{"status": "NOT_VERIFIED", "note": "nothing stored for this query"}]
        return [{"content": r[0], "source": r[1], "confidence": r[2], "status": r[3], "time": r[4]} for r in rows]

