import os
import sqlite3, json, os, datetime
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")
def _get_connection():
    return sqlite3.connect(DB_PATH)
def init_world_model():
    conn = _get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS state_history (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_name TEXT, state_json TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_name TEXT, predicted_state_json TEXT, confidence REAL, made_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, observed_outcome TEXT, outcome_accuracy REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS transitions (entity_name TEXT, from_state TEXT, to_state TEXT, count INTEGER DEFAULT 1, PRIMARY KEY (entity_name, from_state, to_state))")
    c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, entity_name TEXT, event_type TEXT, payload TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()
def update_entity_state(entity_name, new_state, conn=None):
    close_conn = False
    if conn is None:
        conn = _get_connection()
        close_conn = True
    current = conn.execute("SELECT state_json FROM state_history WHERE entity_name = ? ORDER BY timestamp DESC LIMIT 1", (entity_name,)).fetchone()
    current_state = json.loads(current[0]) if current else None
    if current_state:
        from_str = json.dumps(current_state, sort_keys=True)
        to_str = json.dumps(new_state, sort_keys=True)
        conn.execute("INSERT INTO transitions (entity_name, from_state, to_state) VALUES (?, ?, ?) ON CONFLICT(entity_name, from_state, to_state) DO UPDATE SET count = count + 1", (entity_name, from_str, to_str))
        delta = compute_delta(current_state, new_state)
        event_payload = json.dumps({"old": current_state, "new": new_state, "delta": delta})
        conn.execute("INSERT INTO events (entity_name, event_type, payload) VALUES (?, 'state_change', ?)", (entity_name, event_payload))
    conn.execute("INSERT INTO state_history (entity_name, state_json) VALUES (?, ?)", (entity_name, json.dumps(new_state)))
    conn.execute("UPDATE nodes SET properties = json_set(COALESCE(properties, '{}'), '$.state', json(?)) WHERE name = ?", (json.dumps(new_state), entity_name))
    if close_conn:
        conn.commit()
        conn.close()
def get_current_state(entity_name):
    conn = _get_connection()
    row = conn.execute("SELECT state_json FROM state_history WHERE entity_name = ? ORDER BY timestamp DESC LIMIT 1", (entity_name,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None
def compute_delta(old_state, new_state):
    deltas = []
    for key in set(old_state.keys()) | set(new_state.keys()):
        if old_state.get(key) != new_state.get(key):
            deltas.append({"key": key, "old": old_state.get(key), "new": new_state.get(key)})
    return deltas
def predict_next_state(entity_name):
    current = get_current_state(entity_name)
    if not current: return None
    current_str = json.dumps(current, sort_keys=True)
    conn = _get_connection()
    row = conn.execute("SELECT to_state, MAX(count) FROM transitions WHERE entity_name = ? AND from_state = ? GROUP BY to_state ORDER BY count DESC LIMIT 1", (entity_name, current_str)).fetchone()
    if not row:
        conn.close()
        return None
    predicted = json.loads(row[0])
    total_row = conn.execute("SELECT SUM(count) FROM transitions WHERE entity_name=? AND from_state=?", (entity_name, current_str)).fetchone()
    total = total_row[0] if total_row[0] else 1
    conn.close()
    confidence = min(0.95, row[1] / total) if total > 0 else 0.5
    conn = _get_connection()
    conn.execute("INSERT INTO predictions (entity_name, predicted_state_json, confidence) VALUES (?, ?, ?)", (entity_name, json.dumps(predicted), confidence))
    conn.commit()
    conn.close()
    return predicted
def record_prediction_outcome(entity_name, observed_state):
    conn = _get_connection()
    pred = conn.execute("SELECT id, predicted_state_json FROM predictions WHERE entity_name = ? AND observed_outcome IS NULL ORDER BY made_at DESC LIMIT 1", (entity_name,)).fetchone()
    if pred:
        pred_state = json.loads(pred[1])
        accuracy = 1.0 if pred_state == observed_state else 0.0
        conn.execute("UPDATE predictions SET observed_outcome = ?, outcome_accuracy = ? WHERE id = ?", (json.dumps(observed_state), accuracy, pred[0]))
    update_entity_state(entity_name, observed_state, conn)
    conn.commit()
    conn.close()
def what_if(entity_name, intervention_state):
    current = get_current_state(entity_name)
    if not current: return {"effect": "unknown entity"}
    simulated_start = dict(current)
    simulated_start.update(intervention_state)
    start_str = json.dumps(simulated_start, sort_keys=True)
    conn = _get_connection()
    row = conn.execute("SELECT to_state, MAX(count) FROM transitions WHERE entity_name=? AND from_state=? GROUP BY to_state ORDER BY count DESC LIMIT 1", (entity_name, start_str)).fetchone()
    if row:
        predicted = json.loads(row[0])
        total_row = conn.execute("SELECT SUM(count) FROM transitions WHERE entity_name=? AND from_state=?", (entity_name, start_str)).fetchone()
        total = total_row[0] if total_row[0] else 1
        confidence = min(0.95, row[1] / total)
    else:
        predicted = simulated_start
        confidence = 0.3
    effects = []
    deps = conn.execute("SELECT n.name, e.relation FROM edges e JOIN nodes n ON e.target_id = n.id WHERE e.source_id = (SELECT id FROM nodes WHERE name=?) AND e.relation IN ('blocks','supports')", (entity_name,)).fetchall()
    for dep_name, rel in deps:
        if rel == 'blocks' and intervention_state.get("status") == "fixed":
            effects.append({"entity": dep_name, "predicted": "unblocked"})
    conn.close()
    return {"current": current, "intervention": intervention_state, "predicted_new_state": predicted, "confidence": confidence, "effects": effects}
