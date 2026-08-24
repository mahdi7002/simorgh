import os
import sqlite3, json, os
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def load_cultural_data():
    data_path = os.path.join(os.path.dirname(__file__), "../../data/cultural_data.json")
    if not os.path.exists(data_path):
        return
    with open(data_path) as f:
        verses = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    for v in verses:
        conn.execute(
            "INSERT OR IGNORE INTO memory_fts (node_id, content) VALUES (?,?)",
            (None, f"{v['poet']}: {v['verse']}")
        )
    conn.commit()
    conn.close()

def search_cultural(query, limit=3):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT content FROM memory_fts WHERE content MATCH ? LIMIT ?",
        (query, limit)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
