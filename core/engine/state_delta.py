def compute_delta(old_state, new_state):
    deltas = []
    for key in set(old_state.keys()) | set(new_state.keys()):
        if old_state.get(key) != new_state.get(key):
            deltas.append({"key": key, "old": old_state.get(key), "new": new_state.get(key)})
    return deltas
