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
    assert body["outputs"]["moalem"] == "پاسخ آموزشی آزمایشی"
    assert body["review"]["approved"] is True
