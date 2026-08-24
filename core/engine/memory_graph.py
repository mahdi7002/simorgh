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
        session_id TEXT, role TEXT, content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS terminal_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT, cwd TEXT, exit_code INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def init_terminal_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS terminal_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT, cwd TEXT, exit_code INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def query_cause_graph(subject):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT e.explanation, n1.name as cause_name FROM edges e JOIN nodes n1 ON e.source_id = n1.id JOIN nodes n2 ON e.target_id = n2.id WHERE e.relation='causes' AND n2.name LIKE ?", ('%'+subject+'%',)).fetchall()
    conn.close()
    return "; ".join([f"{r[1]}: {r[0]}" for r in rows]) if rows else ""

def save_interaction(query, response):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO nodes (type, name, properties) VALUES (?,?,?)", ("event", query[:50], json.dumps({"response": response[:200]})))
    conn.commit()
    conn.close()

def add_node(type_, name, properties=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO nodes (type, name, properties) VALUES (?,?,?)", (type_, name, json.dumps(properties or {})))
    conn.execute("INSERT OR IGNORE INTO memory_fts (node_id, content) VALUES ((SELECT id FROM nodes WHERE name=?), ?)", (name, name))
    conn.commit()
    conn.close()

def add_edge(source_name, target_name, relation, explanation="", confidence=1.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO nodes (type, name) VALUES ('concept', ?)", (source_name,))
    c.execute("INSERT OR IGNORE INTO nodes (type, name) VALUES ('concept', ?)", (target_name,))
    conn.commit()
    c.execute("SELECT id FROM nodes WHERE name=?", (source_name,))
    src = c.fetchone()
    c.execute("SELECT id FROM nodes WHERE name=?", (target_name,))
    tgt = c.fetchone()
    if src and tgt:
        c.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation, confidence, explanation) VALUES (?,?,?,?,?)", (src[0], tgt[0], relation, confidence, explanation))
    conn.commit()
    conn.close()

def search_nodes_by_keyword(keyword):
    """جستجوی گره‌ها با FTS5"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT n.name, n.type FROM memory_fts f JOIN nodes n ON f.node_id = n.id WHERE f.content MATCH ?", (keyword,)).fetchall()
    conn.close()
    return [{"name": r[0], "type": r[1]} for r in rows]

def find_related_nodes(node_name, relation=None, direction="outgoing", max_depth=1):
    conn = sqlite3.connect(DB_PATH)
    results, visited = [], set()
    def traverse(current_name, depth):
        if depth > max_depth or current_name in visited: return
        visited.add(current_name)
        if direction in ("outgoing", "both"):
            q = "SELECT n2.name, e.relation, n2.type FROM edges e JOIN nodes n1 ON e.source_id = n1.id JOIN nodes n2 ON e.target_id = n2.id WHERE n1.name = ?"
            p = [current_name]
            if relation:
                q += " AND e.relation = ?"
                p.append(relation)
            for r in conn.execute(q, p).fetchall():
                results.append({"source": current_name, "target": r[0], "relation": r[1], "target_type": r[2]})
                traverse(r[0], depth+1)
        if direction in ("incoming", "both"):
            q = "SELECT n1.name, e.relation, n1.type FROM edges e JOIN nodes n1 ON e.source_id = n1.id JOIN nodes n2 ON e.target_id = n2.id WHERE n2.name = ?"
            p = [current_name]
            if relation:
                q += " AND e.relation = ?"
                p.append(relation)
            for r in conn.execute(q, p).fetchall():
                results.append({"source": r[0], "target": current_name, "relation": r[1], "source_type": r[2]})
                traverse(r[0], depth+1)
    traverse(node_name, 0)
    conn.close()
    return results

def seed_unified_graph():
    relations = [
        ("Mahdi", "Build Simorgh", "Wants", "هدف اصلی"),
        ("Low RAM", "Build Simorgh", "Blocks", "محدودیت سخت‌افزاری"),
        ("TV Failure", "Watch Movie", "Blocks", "خرابی تلویزیون"),
        ("Power Outage", "Watch Movie", "Blocks", "قطع برق"),
        ("Printer Failure", "Print Document", "Blocks", "خرابی پرینتر"),
        ("No Paper", "Print Document", "Blocks", "کاغذ تمام شده"),
        ("Mahdi", "Watch Movie", "Wants", "می‌خواهد فیلم ببیند"),
        ("Mahdi", "Print Document", "Wants", "می‌خواهد چاپ کند"),
        ("Mahdi", "Cook Food", "Wants", "می‌خواهد غذا بپزد"),
        ("Broken Oven", "Cook Food", "Blocks", "فر خراب است"),
        ("Watch Movie", "Relaxation", "Supports", "فیلم دیدن برای آرامش"),
        ("Print Document", "Work", "Supports", "چاپ برای کار"),
        ("Cook Food", "Health", "Supports", "غذا برای سلامتی"),
    ]
    for s, t, r, e in relations:
        add_edge(s, t, r, e)

if __name__ == "__main__":
    init_db()
    seed_unified_graph()
    print("✔ دیتابیس و گراف اولیه ساخته شدند")

def cache_response(query, response):
    """ذخیره پاسخ در کش سریع برای بازیابی فوری"""
    import hashlib
    qhash = hashlib.md5(query.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO fast_cache (hash, response, intent) VALUES (?, ?, 'cached')", (qhash, response))
    conn.commit()
    conn.close()
