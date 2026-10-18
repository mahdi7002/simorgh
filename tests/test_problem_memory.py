from __future__ import annotations

from core.mother.problem_memory import ProblemMemory


def make(tmp_path):
    return ProblemMemory(tmp_path / "mother.db")


def test_fingerprint_is_stable(tmp_path):
    pm = make(tmp_path)
    a = pm.fingerprint("llama", "timeout", {"endpoint": "/v1/chat", "slot": 1})
    b = pm.fingerprint("llama", "timeout", {"slot": 1, "endpoint": "/v1/chat"})
    assert a == b


def test_incident_deduplicates_open_occurrences(tmp_path):
    pm = make(tmp_path)
    a = pm.record_incident(component="x", failure_type="y", severity="WARNING", detected_by="test", signature={"a": 1})
    b = pm.record_incident(component="x", failure_type="y", severity="WARNING", detected_by="test", signature={"a": 1})
    assert a["incident_id"] == b["incident_id"]
    row = pm.get_incident(a["incident_id"])["incident"]
    assert row["occurrence_count"] == 2


def test_resolution_only_becomes_lesson_after_verification(tmp_path):
    pm = make(tmp_path)
    inc = pm.record_incident(component="llama", failure_type="timeout", severity="WARNING", detected_by="test", signature={"endpoint": "/v1/chat"})
    pm.record_attempt(inc["incident_id"], actor_type="human", method="restart", action="restart service", success=True, kind="resolution")
    assert pm.lessons() == []
    pm.verify_resolution(inc["incident_id"], verifier_type="deterministic", verified=True, useful=True, evidence={"health": "ok"})
    lessons = pm.lessons(component="llama", failure_type="timeout")
    assert len(lessons) == 1
    assert lessons[0]["method"] == "restart"
    assert lessons[0]["verification_count"] == 1


def test_secret_redaction(tmp_path):
    pm = make(tmp_path)
    inc = pm.record_incident(component="x", failure_type="secret", severity="INFO", detected_by="test", symptom="token=SECRET123")
    row = pm.get_incident(inc["incident_id"])["incident"]
    assert "SECRET123" not in (row["symptom"] or "")
    assert "[REDACTED]" in (row["symptom"] or "")


def test_recovery_creates_verified_lesson(tmp_path):
    pm = make(tmp_path)
    sig = {"signal": "swap_used_pct=PRESSURE"}
    inc = pm.record_incident(component="system-resource", failure_type="resource_pressure", severity="PRESSURE", detected_by="resource_manager", signature=sig, evidence={"swap": 70})
    out = pm.recover_by_signature(component="system-resource", failure_type="resource_pressure", signature=sig, verifier_type="resource_manager", evidence={"swap": 20})
    assert out and out[0]["verification"]["verified"] is True
    lessons = pm.lessons(component="system-resource", failure_type="resource_pressure")
    assert lessons and lessons[0]["success_count"] == 1

def test_connect_context_closes_sqlite_connection(tmp_path):
    import sqlite3

    pm = ProblemMemory(tmp_path / "mother.db")

    with pm._connect() as conn:
        conn.execute("SELECT 1")

    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError as exc:
        assert "closed database" in str(exc).lower()
    else:
        raise AssertionError("ProblemMemory connection remained open")
