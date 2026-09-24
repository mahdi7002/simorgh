from fastapi.testclient import TestClient
import main


def test_orchestrate_endpoint_without_real_llm(monkeypatch):
    fake_result = {
        "query": "سلام",
        "selected_agents": ["hakim", "moalem"],
        "outputs": {
            "hakim": "پاسخ آزمایشی",
            "moalem": "پاسخ آموزشی آزمایشی",
        },
        "tool_results": {},
        "review": {
            "approved": True,
            "warnings": [],
            "checks": ["non_empty_output"],
            "route_reason": "test",
        },
        "final_output": "[hakim]\nپاسخ آزمایشی\n\n[moalem]\nپاسخ آموزشی آزمایشی",
        "response_blocked": False,
    }

    monkeypatch.setattr(
        main.orchestrator,
        "run",
        lambda query, max_agents=2: fake_result,
    )

    c = TestClient(main.app)

    r = c.post(
        "/orchestrate",
        data={"query": "سلام"},
    )

    assert r.status_code == 200

    body = r.json()

    assert body["selected_agents"] == ["hakim", "moalem"]
    assert body["outputs"]["hakim"] == "پاسخ آزمایشی"
    assert body["response"] == fake_result["final_output"]
    assert body["review"]["approved"] is True


def test_orchestrate_endpoint_hides_unapproved_agent_outputs(monkeypatch):
    fake_result = {
        "query": "منبع دقیق این ادعا را بگو",
        "selected_agents": ["hakim"],
        "outputs": {"hakim": "طبق منابع این ادعا درست است."},
        "tool_results": {},
        "review": {
            "approved": False,
            "warnings": ["evidence_sensitive_request_without_tool_evidence"],
            "checks": ["evidence_gate"],
        },
        "final_output": "[NOT_VERIFIED] پاسخ به دلیل نبود شواهد کافی تأیید نشد و نمایش داده نمی‌شود.",
        "response_blocked": True,
    }

    monkeypatch.setattr(
        main.orchestrator,
        "run",
        lambda query, max_agents=2: fake_result,
    )

    body = TestClient(main.app).post(
        "/orchestrate",
        data={"query": "منبع دقیق این ادعا را بگو"},
    ).json()

    assert body["review"]["approved"] is False
    assert body["response_blocked"] is True
    assert body["outputs"] == {}
    assert body["response"].startswith("[NOT_VERIFIED]")
