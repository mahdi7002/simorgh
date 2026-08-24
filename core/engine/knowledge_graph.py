import os
import sqlite3, os, json
import networkx as nx

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def init_knowledge_graph():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    concepts = ["علم", "هنر", "اخلاق", "تاریخ", "طبیعت", "انسان", "عشق"]
    for name in concepts:
        c.execute("INSERT OR IGNORE INTO nodes (type, name) VALUES ('concept', ?)", (name,))
    conn.commit()
    conn.close()

def add_relation(concept1, concept2, relation, explanation="", confidence=1.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM nodes WHERE name=? AND type='concept'", (concept1,))
    src = c.fetchone()
    c.execute("SELECT id FROM nodes WHERE name=? AND type='concept'", (concept2,))
    tgt = c.fetchone()
    if src and tgt:
        c.execute("INSERT INTO edges (source_id, target_id, relation, explanation, confidence) VALUES (?,?,?,?,?)",
                  (src[0], tgt[0], relation, explanation, confidence))
    conn.commit()
    conn.close()

def load_graph():
    G = nx.Graph()
    conn = sqlite3.connect(DB_PATH)
    nodes = conn.execute("SELECT id, name FROM nodes WHERE type='concept'").fetchall()
    for n in nodes:
        G.add_node(n[0], name=n[1])
    edges = conn.execute("SELECT source_id, target_id, relation, explanation FROM edges WHERE relation='related_to'").fetchall()
    for e in edges:
        G.add_edge(e[0], e[1], relation=e[2], explanation=e[3])
    conn.close()
    return G

def find_hidden_connections():
    G = load_graph()
    suggestions = []
    for n1 in G.nodes():
        for n2 in G.nodes():
            if n1 < n2 and not G.has_edge(n1, n2):
                try:
                    path = nx.shortest_path(G, n1, n2)
                    if len(path) > 2:
                        suggestions.append((G.nodes[n1]['name'], G.nodes[n2]['name'], len(path)-1))
                except nx.NetworkXNoPath:
                    continue
    return sorted(suggestions, key=lambda x: x[2])[:10]
