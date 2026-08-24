import os
import sqlite3, json, os, datetime, re
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from . import truth
from . import meta_reflection

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "../../data/snapshots")
PROPOSAL_DIR = os.path.join(os.path.dirname(__file__), "../../data/reflection_proposals")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(PROPOSAL_DIR, exist_ok=True)

def load_episodes(limit=200):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, query, goal, obstacle, reasoning_path, timestamp FROM request_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"id": r[0], "query": r[1], "goal": r[2], "obstacle": r[3], "reasoning_path": json.loads(r[4]) if r[4] else [], "timestamp": r[5]} for r in rows]

def cluster_queries(episodes):
    texts = [ep["query"] for ep in episodes]
    if len(texts) < 3:
        return []
    try:
        vec = TfidfVectorizer(max_features=100)
        X = vec.fit_transform(texts)
        clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine').fit(X)
        labels = clustering.labels_
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            if label != -1:
                clusters[label].append(episodes[i])
        return list(clusters.values())
    except:
        return []

def propose_new_knowledge(cluster):
    proposals = []
    obstacle = max(set([ep["obstacle"] for ep in cluster if ep["obstacle"]]), key=lambda x: [ep["obstacle"] for ep in cluster].count(x)) if any(ep["obstacle"] for ep in cluster) else None
    goal = max(set([ep["goal"] for ep in cluster if ep["goal"]]), key=lambda x: [ep["goal"] for ep in cluster].count(x)) if any(ep["goal"] for ep in cluster) else None
    if obstacle and goal:
        ver = truth.verify_statement(obstacle, 'blocks', goal)
        if ver["consistent"]:
            return []
        proposals.append({
            "type": "blocks",
            "source": obstacle,
            "target": goal,
            "confidence": 0.4,
            "explanation": f"کشف خودکار از {len(cluster)} پرسش مشابه",
            "knowledge_type": "hypothesis"
        })
    return proposals

def detect_architecture_weaknesses():
    issues = []
    agent_files = [f.split('.')[0] for f in os.listdir("agents") if f.endswith('.yaml')]
    conn = sqlite3.connect(DB_PATH)
    for agent in agent_files:
        count = conn.execute("SELECT COUNT(*) FROM request_log WHERE selected_agents LIKE ?", (f'%{agent}%',)).fetchone()[0]
        if count == 0:
            issues.append({"component": f"agent/{agent}", "issue": "No recent usage", "suggestion": "Consider removing or reviewing"})
    tables = ["nodes", "edges", "request_log", "short_term_memory", "fast_cache"]
    for tbl in tables:
        rows = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        if rows == 0 and tbl not in ["request_log", "short_term_memory"]:
            issues.append({"component": f"db/{tbl}", "issue": "Empty table", "suggestion": "Maybe unnecessary"})
    conn.close()
    return issues

def create_snapshot():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = os.path.join(SNAPSHOT_DIR, f"graph_{timestamp}.json")
    conn = sqlite3.connect(DB_PATH)
    nodes = conn.execute("SELECT * FROM nodes").fetchall()
    edges = conn.execute("SELECT * FROM edges").fetchall()
    conn.close()
    with open(snap_path, 'w') as f:
        json.dump({"nodes": [tuple(r) for r in nodes], "edges": [tuple(r) for r in edges]}, f)
    return snap_path

def run_reflection(human_approval=True):
    print(f"[{datetime.datetime.now()}] Reflection cycle started.")
    snapshot = create_snapshot()
    print(f"Snapshot saved: {snapshot}")
    episodes = load_episodes()
    clusters = cluster_queries(episodes)
    proposals = []
    for cluster in clusters:
        proposals.extend(propose_new_knowledge(cluster))
    issues = detect_architecture_weaknesses()
    if issues:
        issue_path = os.path.join(PROPOSAL_DIR, "architecture_issues.json")
        with open(issue_path, 'w') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
        print(f"Architecture issues found → {issue_path}")
    final_proposals = []
    for p in proposals:
        ver = truth.verify_statement(p["source"], p["type"], p["target"])
        if ver["consistent"] == False:
            continue
        if ver["consistent"] is True:
            p["confidence"] = max(p["confidence"], ver["confidence"] * 0.8)
        final_proposals.append(p)
    if final_proposals:
        prop_path = os.path.join(PROPOSAL_DIR, f"proposals_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(prop_path, 'w') as f:
            json.dump(final_proposals, f, ensure_ascii=False, indent=2)
        print(f"Proposals saved to {prop_path}")
        if not human_approval:
            apply_proposals(final_proposals)
            print("Proposals auto-applied.")
        else:
            print("Awaiting human approval.")
    else:
        print("No new proposals.")
    return final_proposals

def apply_proposals(proposals):
    conn = sqlite3.connect(DB_PATH)
    for p in proposals:
        if p["type"] == "blocks":
            truth.add_fact(p["source"], "blocks", p["target"],
                           explanation=p.get("explanation", ""),
                           confidence=p["confidence"],
                           knowledge_type=p.get("knowledge_type", "hypothesis"))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_reflection(human_approval=True)

def run_full_reflection():
    """بازتاب کامل روی تمام حافظه‌های موجود (نه فقط اخیر)."""
    print(f"[{datetime.datetime.now()}] Full Reflection started...")
    snapshot = create_snapshot()
    print(f"Snapshot saved: {snapshot}")

    # بارگیری تمام قسمت‌های history (محدودیت را بردارید)
    episodes = load_episodes(limit=10000)
    clusters = cluster_queries(episodes)
    proposals = []
    for cluster in clusters:
        proposals.extend(propose_new_knowledge(cluster))

    issues = detect_architecture_weaknesses()
    if issues:
        issue_path = os.path.join(PROPOSAL_DIR, "architecture_issues.json")
        with open(issue_path, 'w') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
        print(f"Architecture issues found → {issue_path}")

    final_proposals = []
    for p in proposals:
        ver = truth.verify_statement(p["source"], p["type"], p["target"])
        if ver["consistent"] == False:
            continue
        if ver["consistent"] is True:
            p["confidence"] = max(p["confidence"], ver["confidence"] * 0.8)
        final_proposals.append(p)

    if final_proposals:
        prop_path = os.path.join(PROPOSAL_DIR, f"full_proposals_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(prop_path, 'w') as f:
            json.dump(final_proposals, f, ensure_ascii=False, indent=2)
        print(f"Full proposals saved to {prop_path}")
        # در بازتاب کامل، اگر human_approval=False باشد، مستقیماً اعمال می‌کنیم
        if not human_approval:
            apply_proposals(final_proposals)
            print("Full proposals auto-applied.")
    else:
        print("No new proposals from full reflection.")

    # به‌روزرسانی Meta-Reflection
    if final_proposals:
        meta_reflection.log_reflection_outcome(len(final_proposals), 0, 0, 1.0)  # accuracy بعد از تأیید آپدیت می‌شود

    print("Full reflection completed.")
