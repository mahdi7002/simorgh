from typing import Optional, List, Dict, Any, Tuple, Union, Set, Callable, Iterable, Sequence  # auto-added by bulk_fix_typing_imports.py
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class WhyEngine:
    def __init__(self, db_path="knowledge/knowledge_graph.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), "../..", db_path)

    def find_cause(self, obstacle: str) -> Optional[str]:
        if not obstacle:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT n.name
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.relation = 'causes' AND e.target_id = (
                SELECT id FROM nodes WHERE name = ? COLLATE NOCASE
            )
            """, (obstacle,))
            cause = cursor.fetchone()
            return cause[0] if cause else None
        except Exception as e:
            logger.error(f"Error in find_cause: {e}")
            return None
        finally:
            conn.close()
