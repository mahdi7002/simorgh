import sqlite3, json, os
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def add_value(name, weight=1.0, parent=None, description=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO nodes (type, name, properties) VALUES ('value', ?, ?)",
                 (name, json.dumps({"weight": weight, "description": description})))
    if parent:
        conn.execute("INSERT OR IGNORE INTO edges (source_id, target_id, relation, explanation) VALUES ((SELECT id FROM nodes WHERE name=?), (SELECT id FROM nodes WHERE name=?), 'parent_of', ?)",
                     (parent, name, f"زیرمجموعه {parent}"))
    conn.commit()
    conn.close()

def get_values():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name, properties FROM nodes WHERE type='value'").fetchall()
    conn.close()
    return [{"name": r[0], "weight": json.loads(r[1]).get("weight", 1.0)} for r in rows]

def enrich_understanding(query, context):
    """Adds value hints to the understanding context before agent processing."""
    values = get_values()
    value_hints = []
    for v in values:
        if v["name"] in query:
            value_hints.append(v["name"])
    context["values"] = value_hints if value_hints else [v["name"] for v in values[:2]]
    return context

def evaluate_action(intent, goal, response_text):
    """Checks if response aligns with core values. Returns alignment report."""
    values = get_values()
    conflicts = []
    health_keywords = ["مضر", "چرب", "ناسالم", "خطرناک"]
    if any(kw in response_text for kw in health_keywords):
        conflicts.append("Health")
    aligned = len(conflicts) == 0
    return {"aligned": aligned, "conflicts": conflicts, "score": 1.0 if aligned else 0.5}

def seed_defaults():
    defaults = [("سلامتی", 0.9, None, "اهمیت سلامت جسم و روان"), ("صداقت", 0.85, None, "ارزش راستگویی"),
                ("خانواده", 0.95, None, "اولویت خانواده"), ("دانش", 0.8, None, "اهمیت یادگیری"), ("انصاف", 0.75, None, "رعایت عدالت")]
    for name, weight, parent, desc in defaults:
        add_value(name, weight, parent, desc)
