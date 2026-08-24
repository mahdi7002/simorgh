import sqlite3
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryEngine:
    def __init__(self, db_path="memory/short_term.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), "../..", db_path)
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_input TEXT,
            system_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            preferences JSON,
            projects JSON,
            recurring_goals JSON,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
        logger.info("Memory database initialized")

    def store_conversation(self, session_id: str, user_input: str, system_response: str, metadata: dict = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, user_input, system_response, metadata) VALUES (?, ?, ?, ?)",
            (session_id, user_input, system_response, json.dumps(metadata) if metadata else None)
        )
        conn.commit()
        conn.close()
        logger.info(f"Stored conversation for session: {session_id}")

    def get_conversation_history(self, session_id: str, limit: int = 10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_input, system_response, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        history = cursor.fetchall()
        conn.close()
        return [{"user": row[0], "system": row[1], "time": row[2]} for row in history]
