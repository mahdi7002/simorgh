import os
import subprocess
import sys

import pytest


def test_fast_llm_uses_fast_timeout(monkeypatch):
    import core.llm_local as llm

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm, "FAST_TIMEOUT", 8.0)
    monkeypatch.setattr(llm, "QUALITY_TIMEOUT", 2.0)

    assert llm.generate("system", "hello", needs_quality=False) == "ok"
    assert captured["url"] == llm.FAST_URL
    assert captured["timeout"] == pytest.approx(8.0)


def test_quality_llm_uses_quality_timeout(monkeypatch):
    import core.llm_local as llm

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm, "FAST_TIMEOUT", 8.0)
    monkeypatch.setattr(llm, "QUALITY_TIMEOUT", 2.0)

    assert llm.generate("system", "hello", needs_quality=True) == "ok"
    assert captured["url"] == llm.QUALITY_URL
    assert captured["timeout"] == pytest.approx(2.0)


def test_reviewer_does_not_treat_failed_tool_as_evidence():
    from core.orchestration import Reviewer

    result = Reviewer().review(
        "منبع دقیق این آیه چیست؟",
        {"hakim": "طبق قرآن این آیه چنین است."},
        {
            "quran_search": {
                "status": "NOT_AVAILABLE",
                "data": None,
                "provenance": {"execution": "local"},
            }
        },
    )

    assert result.approved is False
    assert "evidence_sensitive_request_without_tool_evidence" in result.warnings


def test_default_registry_exposes_sensor_status():
    from core.tools import build_default_registry

    registry = build_default_registry()
    assert registry.available("sensor_status")

    result = registry.execute("sensor_status", "وضعیت سیستم")
    assert result.status == "OK"
    assert result.provenance["execution"] == "local"
    assert 0.0 <= result.data["memory_percent"] <= 100.0
    assert 0.0 <= result.data["disk_percent"] <= 100.0


def test_external_bind_without_key_fails_closed():
    env = os.environ.copy()
    env["SIMORGH_HOST"] = "0.0.0.0"
    env.pop("SIMORGH_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "Refusing non-loopback bind" in combined


def test_external_bind_with_key_installs_auth_middleware():
    env = os.environ.copy()
    env["SIMORGH_HOST"] = "0.0.0.0"
    env["SIMORGH_KEY"] = "test-only-key"

    script = (
        "import main; "
        "print(any(getattr(m, 'cls', None).__name__ == 'BaseHTTPMiddleware' "
        "for m in main.app.user_middleware))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "True" in result.stdout


def test_external_bind_auth_enforced_end_to_end():
    env = os.environ.copy()
    env["SIMORGH_HOST"] = "0.0.0.0"
    env["SIMORGH_KEY"] = "test-only-key"

    script = r'''
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

assert client.get("/health").status_code == 200
assert client.get("/personas").status_code == 401
assert client.get("/personas", headers={"x-token": "wrong"}).status_code == 401
assert client.get("/personas", headers={"x-token": "test-only-key"}).status_code == 200
print("AUTH_E2E_PASS")
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "AUTH_E2E_PASS" in result.stdout


def test_session_ids_are_hashed_and_distinct(monkeypatch):
    import main
    from fastapi import Request

    def fake_request(value):
        scope = {
            "type": "http",
            "headers": [(b"x-simorgh-session", value.encode())],
        }
        return Request(scope)

    one = main._session_id(fake_request("alice-session"))
    two = main._session_id(fake_request("bob-session"))

    assert one != two
    assert len(one) == 64
    assert "alice-session" not in one


def test_chat_response_disclosure_and_security_headers(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    monkeypatch.setattr(main, "chat_ask", lambda query, agent="hakim": "پاسخ آزمایشی")
    monkeypatch.setattr(main.memory, "store_conversation", lambda *args, **kwargs: None)

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        data={"query": "سلام", "agent": "hakim"},
        headers={"x-simorgh-session": "test-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_disclosure"] == main.AI_DISCLOSURE
    assert response.headers["x-simorgh-ai-generated"] == "true"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
