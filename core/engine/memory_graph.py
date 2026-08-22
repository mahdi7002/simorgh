import sqlite3, json
DB_PATH = "data/simorgh.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        properties TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER, target_id INTEGER,
        relation TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        explanation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(source_id) REFERENCES nodes(id),
        FOREIGN KEY(target_id) REFERENCES nodes(id)
    )""")
    c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        node_id, content, tokenize='unicode61'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS fast_cache (
        hash TEXT PRIMARY KEY, response TEXT, intent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS personal_memory (
        key TEXT PRIMARY KEY, value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT, week TEXT, title TEXT, description TEXT,
        done INTEGER DEFAULT 0, tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS short_term_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def query_cause_graph(subject):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT e.explanation, n1.name as cause_name
           FROM edges e
           JOIN nodes n1 ON e.source_id = n1.id
           JOIN nodes n2 ON e.target_id = n2.id
           WHERE e.relation='causes' AND n2.name LIKE ?""",
        ('%'+subject+'%',)
    ).fetchall()
    conn.close()
    if rows:
        causes = [f"{r[1]}: {r[0]}" for r in rows]
        return "; ".join(causes)
    return ""

def save_interaction(query, response):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO nodes (type, name, properties) VALUES (?,?,?)",
              ("event", query[:50], json.dumps({"response": response[:200]})))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✔ دیتابیس آماده شد")
