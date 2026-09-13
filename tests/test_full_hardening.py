from pathlib import Path

from fastapi.testclient import TestClient

import main
from core.memory import MemoryEngine
from core.orchestration import Blackboard, Dispatcher, Reviewer, Orchestrator
from core.self_improvement_policy import ChangeRequest, RiskLevel, decision


def test_memory_provenance_is_separate(tmp_path):
    memory_db = tmp_path / "memory.db"
    m = MemoryEngine(db_path=memory_db)

    m.store_conversation("s1", "hello", "world", {"x": 1})
    m.store_with_provenance(
        "verified text",
        source="unit-test",
        confidence=0.9,
        tags=["test"],
        status="KNOWN",
    )

    assert memory_db.exists()
    assert m.provenance_db.exists()
    assert m.provenance_db != memory_db

    history = m.get_conversation_history("s1")
    assert history
    found = m.search_with_provenance("verified")
    assert found[0]["status"] == "KNOWN"


def test_blackboard_preserves_shared_state():
    b = Blackboard("test")
    b.selected_agents = ["hakim", "amel"]
    b.record_output("hakim", "one")
    b.record_output("amel", "two")
    b.record_tool_result("x", {"ok": True})

    state = b.as_dict()

    assert state["outputs"]["hakim"] == "one"
    assert state["outputs"]["amel"] == "two"
    assert state["tool_results"]["x"]["ok"] is True


def test_dispatcher_is_cpu_cheap_and_bounded():
    d = Dispatcher()

    a = d.dispatch("چرا این اتفاق افتاد؟", max_agents=2)
    assert len(a.agents) <= 2
    assert "hakim" in a.agents

    b = d.dispatch("چیکار کنم این را بسازم؟", max_agents=2)
    assert len(b.agents) <= 2
    assert "amel" in b.agents


def test_reviewer_does_not_claim_truth():
    r = Reviewer().review(
        "منبع دقیق را بگو",
        {"hakim": "این یک پاسخ است."},
        {},
    )

    assert r.approved is False
    assert "evidence_sensitive_request_without_evidence" in r.warnings


def test_governance_never_allows_privilege_or_policy_changes():
    assert decision(
        ChangeRequest(
            RiskLevel.REVERSIBLE_STATE,
            privilege_gain=True,
        )
    ) == "HUMAN_GATE"

    assert decision(
        ChangeRequest(
            RiskLevel.REVERSIBLE_STATE,
            policy_change=True,
        )
    ) == "HUMAN_GATE"

    assert decision(
        ChangeRequest(
            RiskLevel.REVERSIBLE_STATE,
            evaluator_change=True,
        )
    ) == "HUMAN_GATE"


def test_orchestrate_endpoint_exists():
    c = TestClient(main.app)
    r = c.post("/orchestrate", data={"query": "سلام"})
    assert r.status_code == 200
    body = r.json()

    assert "selected_agents" in body
    assert "outputs" in body
    assert "review" in body
    assert len(body["selected_agents"]) <= 2


def test_health_and_api_surface():
    c = TestClient(main.app)

    assert c.get("/health").status_code == 200
    assert c.get("/dashboard/").status_code in (200, 404)
    assert c.get("/personas").status_code == 200
