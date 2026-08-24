from typing import Optional, List, Dict, Any, Tuple, Union, Set, Callable, Iterable, Sequence  # auto-added by bulk_fix_typing_imports.py
from typing import Tuple, Optional
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class UnderstandingEngine:
    def __init__(self, db_path="knowledge/knowledge_graph.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), "../..", db_path)
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT,
            properties JSON
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            target_id INTEGER,
            relation TEXT,
            FOREIGN KEY (source_id) REFERENCES nodes(id),
            FOREIGN KEY (target_id) REFERENCES nodes(id)
        )
        """)
        conn.commit()
        conn.close()
        logger.info("Knowledge graph database initialized")

    def detect_intent(self, query: str) -> str:
        query_lower = query.lower()
        if any(word in query_lower for word in ["چرا", "چگونه", "چطور", "چرا که"]):
            return "question"
        elif any(word in query_lower for word in ["بکن", "اجرای", "انجام بده", "run", "execute"]):
            return "command"
        elif any(word in query_lower for word in ["می‌خواهم", "میخوام", "میشه", "can you"]):
            return "request"
        else:
            return "statement"

    def extract_goal_obstacle(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM nodes WHERE type='goal' AND name LIKE ? COLLATE NOCASE", (f"%{query}%",))
        goal = cursor.fetchone()
        goal = goal[0] if goal else None

        cursor.execute("SELECT name FROM nodes WHERE type='obstacle' AND name LIKE ? COLLATE NOCASE", (f"%{query}%",))
        obstacle = cursor.fetchone()
        obstacle = obstacle[0] if obstacle else None

        conn.close()
        return goal, obstacle
