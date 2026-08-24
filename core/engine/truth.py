import os
import sqlite3, os, json
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

KNOWLEDGE_TYPES = ["observation", "hypothesis", "belief", "fact"]

def compute_multidimensional_confidence(evidence_conf=0.5, source_conf=0.5, recency_conf=0.5, consistency_conf=0.5):
    weights = {"evidence": 0.4, "source": 0.3, "recency": 0.2, "consistency": 0.1}
    combined = (evidence_conf * weights["evidence"] + 
                source_conf * weights["source"] + 
                recency_conf * weights["recency"] + 
                consistency_conf * weights["consistency"])
    return {
        "evidence": evidence_conf,
        "source": source_conf,
        "recency": recency_conf,
        "consistency": consistency_conf,
        "combined": round(combined, 2)
    }

def verify_statement(subject, relation, object_, knowledge_type="observation"):
    conn = sqlite3.connect(DB_PATH)
    edge = conn.execute("""
        SELECT e.confidence, e.explanation, e.properties
        FROM edges e
        JOIN nodes n1 ON e.source_id = n1.id
        JOIN nodes n2 ON e.target_id = n2.id
        WHERE n1.name=? AND n2.name=? AND e.relation=?
    """, (subject, object_, relation)).fetchone()
    if edge:
        props = json.loads(edge[2]) if edge[2] else {}
        existing_type = props.get("knowledge_type", "unknown")
        conf = props.get("confidence", {"combined": 0.5})
        if isinstance(conf, (int, float)):
            conf = {"combined": conf}
        return {"consistent": True, "confidence": conf.get("combined", 0.5), "source": "graph", "explanation": edge[1], "existing_type": existing_type}
    contradictory = {"blocks": "supports", "supports": "blocks", "causes": "prevents"}
    if relation in contradictory:
        contra_rel = contradictory[relation]
        cont = conn.execute("""
            SELECT e.confidence, e.properties FROM edges e
            JOIN nodes n1 ON e.source_id = n1.id
            JOIN nodes n2 ON e.target_id = n2.id
            WHERE n1.name=? AND n2.name=? AND e.relation=?
        """, (subject, object_, contra_rel)).fetchone()
        if cont:
            return {"consistent": False, "confidence": cont[0], "conflict": f"{subject} {contra_rel} {object_} already exists"}
    conn.close()
    return {"consistent": None, "confidence": 0.0}

def add_fact(subject, relation, object_, explanation="", confidence=None, source="user", knowledge_type="observation", evidence_conf=0.5, source_conf=0.5, recency_conf=0.5, consistency_conf=0.5):
    if confidence is None:
        confidence = compute_multidimensional_confidence(evidence_conf, source_conf, recency_conf, consistency_conf)
    elif isinstance(confidence, (int, float)):
        base = compute_multidimensional_confidence(evidence_conf, source_conf, recency_conf, consistency_conf)
        base["combined"] = round(base["combined"] * 0.8 + 0.2 * confidence, 2)
        confidence = base
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO nodes (type, name) VALUES ('concept', ?)", (subject,))
    conn.execute("INSERT OR IGNORE INTO nodes (type, name) VALUES ('concept', ?)", (object_,))
    properties = json.dumps({
        "knowledge_type": knowledge_type,
        "source": source,
        "confidence": confidence,
        "added_by": "truth_layer"
    })
    conn.execute("""INSERT OR REPLACE INTO edges
        (source_id, target_id, relation, confidence, explanation, properties)
        VALUES (
            (SELECT id FROM nodes WHERE name=?),
            (SELECT id FROM nodes WHERE name=?),
            ?, ?, ?, ?
        )""", (subject, object_, relation, confidence["combined"], f"[{source}] {explanation}", properties))
    conn.commit()
    conn.close()

def classify_edges():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""UPDATE edges SET properties = json_set(properties, '$.knowledge_type', 'fact')
                    WHERE json_extract(properties, '$.confidence.combined') >= 0.8 
                    AND json_extract(properties, '$.knowledge_type') IN ('observation', 'hypothesis')""")
    conn.commit()
    conn.close()
