import os
import sqlite3, time, os, json

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def init_observability():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS request_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        intent TEXT,
        goal TEXT,
        obstacle TEXT,
        reasoning_path TEXT,
        selected_agents TEXT,
        response_time_ms REAL,
        memory_hits INTEGER DEFAULT 0,
        cache_hit INTEGER DEFAULT 0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def log_request(query, resolved, agent_resp, elapsed_ms):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO request_log
        (query, intent, goal, obstacle, reasoning_path, selected_agents, response_time_ms, memory_hits, cache_hit)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (query,
         resolved.get("intent"),
         resolved.get("goal"),
         resolved.get("obstacle"),
         json.dumps(resolved.get("reasoning_path", [])),
         json.dumps(list(agent_resp.keys()) if isinstance(agent_resp, dict) else []),
         elapsed_ms,
         resolved.get("memory_hits", 0),
         1 if resolved.get("cached") else 0))
    conn.commit()
    conn.close()

def get_recent_stats(limit=20):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM request_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows
