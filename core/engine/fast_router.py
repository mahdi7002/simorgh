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

    goal = understanding.extract_goal(query)
    cause = why_engine.find_cause(query)
    emotion = emotion_detector.detect_emotion(query)
    conn.close()
    return {
        "cached": False,
        "intent": goal["intent"],
        "understanding": goal["description"],
        "cause": cause,
        "emotion": emotion,
        "needs_agent": True
    }
