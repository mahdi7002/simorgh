import os
import json, sqlite3
from collections import deque
from . import world_model
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")
def plan_to_goal(entity_name, goal_state, max_depth=3):
    current = world_model.get_current_state(entity_name)
    if not current: return {"error": "unknown entity"}
    if current == goal_state: return {"steps": 0, "path": []}
    conn = sqlite3.connect(DB_PATH)
    visited = set()
    queue = deque()
    queue.append((current, []))
    visited.add(json.dumps(current, sort_keys=True))
    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth: continue
        state_str = json.dumps(state, sort_keys=True)
        next_rows = conn.execute("SELECT to_state, SUM(count) FROM transitions WHERE entity_name=? AND from_state=? GROUP BY to_state", (entity_name, state_str)).fetchall()
        for to_str, count in next_rows:
            next_state = json.loads(to_str)
            if json.dumps(next_state, sort_keys=True) in visited: continue
            new_path = path + [(state, next_state)]
            if next_state == goal_state:
                conn.close()
                return {"steps": len(new_path), "path": new_path}
            visited.add(json.dumps(next_state, sort_keys=True))
            queue.append((next_state, new_path))
    conn.close()
    return {"steps": -1, "message": "no path found within depth limit"}
