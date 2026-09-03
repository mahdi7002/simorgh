import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def search_knowledge(query, limit=3):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT n.name, f.content FROM memory_fts f JOIN nodes n ON f.node_id = n.id WHERE f.content MATCH ? LIMIT ?", (query, limit)).fetchall()
    if not rows:
        for word in query.split():
            if len(word) > 2:
                rows = conn.execute("SELECT n.name, f.content FROM memory_fts f JOIN nodes n ON f.node_id = n.id WHERE f.content MATCH ? LIMIT ?", (word, limit)).fetchall()
                if rows: break
    conn.close()
    return [{"title": r[0], "content": r[1][:500]} for r in rows]
