import hashlib, sqlite3
from . import understanding, why_engine, emotion_detector

DB_PATH = "data/simorgh.db"

def resolve(query):
    qhash = hashlib.md5(query.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT response FROM fast_cache WHERE hash=?", (qhash,)).fetchone()
    if row:
        conn.close()
        return {"cached": True, "response": row[0]}

    goal_data = understanding.find_goal_and_obstacle(query)
    cause = why_engine.find_cause(query)
    emotion = emotion_detector.detect_emotion(query)
    conn.close()

    # ensure 'intent' exists
    intent = goal_data.get("intent", "general")
    return {
        "cached": False,
        "intent": intent,
        "goal": goal_data.get("goal", ""),
        "obstacle": goal_data.get("obstacle", ""),
        "reasoning_path": goal_data.get("reasoning_path", []),
        "understanding": goal_data.get("description", ""),
        "cause": cause or "",
        "emotion": emotion or "درک_و_فهم",
        "needs_agent": True
    }
