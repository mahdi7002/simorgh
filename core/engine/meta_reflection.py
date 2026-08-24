import os
import json, os, datetime
META_LOG = os.path.join(os.path.dirname(__file__), "../../data/meta_reflection.json")

def log_reflection_outcome(total_proposals, applied, rejected, accuracy_after_approval=None):
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_proposals": total_proposals,
        "applied": applied,
        "rejected": rejected,
        "accuracy": accuracy_after_approval if accuracy_after_approval is not None else (applied / total_proposals if total_proposals > 0 else 0)
    }
    if os.path.exists(META_LOG):
        with open(META_LOG, 'r') as f:
            log = json.load(f)
    else:
        log = []
    log.append(entry)
    with open(META_LOG, 'w') as f:
        json.dump(log, f, indent=2)

def get_meta_stats():
    if not os.path.exists(META_LOG):
        return None
    with open(META_LOG, 'r') as f:
        log = json.load(f)
    if not log:
        return None
    total = len(log)
    recent = log[-5:]
    avg_accuracy = sum(e["accuracy"] for e in recent) / len(recent)
    return {"total_cycles": total, "recent_accuracy": round(avg_accuracy, 2)}
