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
    monkeypatch.setenv("SIMORGH_LLM_FAST_URL", llm.FAST_URL)
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
    monkeypatch.setenv("SIMORGH_LLM_QUALITY_URL", llm.QUALITY_URL)
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

    monkeypatch.setattr(main, "chat_ask", lambda query, agent="hakim", return_metadata=False: ("پاسخ آزمایشی", True))
    monkeypatch.setattr(main.memory, "store_conversation", lambda *args, **kwargs: None)

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        data={"query": "سلام", "agent": "hakim"},
        headers={"x-simorgh-session": "test-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_generated"] is True
    assert body["ai_disclosure"] == main.AI_DISCLOSURE
    assert body["knowledge_disclosure"] is None
    assert body["disclosure"] == main.AI_DISCLOSURE
    assert response.headers["x-simorgh-ai-generated"] == "true"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_chat_database_first_disclosure_is_not_ai_generated(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    monkeypatch.setattr(
        main,
        "chat_ask",
        lambda query, agent="hakim", return_metadata=False: ("پاسخ مستقیم از پایگاه دانش", False),
    )
    monkeypatch.setattr(main.memory, "store_conversation", lambda *args, **kwargs: None)

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        data={"query": "یک پرسش محلی", "agent": "hakim"},
        headers={"x-simorgh-session": "test-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_generated"] is False
    assert body["ai_disclosure"] is None
    assert body["knowledge_disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert body["disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert response.headers["x-simorgh-ai-generated"] == "false"


def test_global_request_body_limit_is_configured():
    import main

    assert main.MAX_REQUEST_BYTES == 10 * 1024 * 1024
    assert any(
        getattr(m, "cls", None).__name__ == "RequestBodyLimitMiddleware"
        for m in main.app.user_middleware
    )


def test_ask_endpoint_reports_database_first_without_fake_ai_disclosure(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    monkeypatch.setattr(
        main.agent_manager,
        "consult",
        lambda *args, return_metadata=False, **kwargs: (
            ("پاسخ مستقیم از پایگاه دانش", False) if return_metadata else "پاسخ مستقیم از پایگاه دانش"
        ),
    )
    monkeypatch.setattr(main.memory, "store_conversation", lambda *args, **kwargs: None)

    client = TestClient(main.app)
    response = client.post(
        "/ask",
        data={"query": "عدالت چیست؟"},
        headers={"x-simorgh-session": "test-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_generated"] is False
    assert body["ai_disclosure"] is None
    assert body["knowledge_disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert body["disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert response.headers["x-simorgh-ai-generated"] == "false"


def test_orchestrate_endpoint_reports_aggregate_provenance(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    result = {
        "query": "سلام",
        "selected_agents": ["hakim"],
        "outputs": {"hakim": "پاسخ مستقیم از پایگاه دانش"},
        "ai_generated": {"hakim": False},
        "tool_results": {},
        "review": {"approved": True, "warnings": [], "checks": []},
    }
    monkeypatch.setattr(main.orchestrator, "run", lambda query, max_agents=2: result)
    monkeypatch.setattr(main.memory, "store_conversation", lambda *args, **kwargs: None)

    client = TestClient(main.app)
    response = client.post(
        "/orchestrate",
        data={"query": "سلام"},
        headers={"x-simorgh-session": "test-session"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_generated"] is False
    assert body["disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert body["ai_disclosure"] is None
    assert body["knowledge_disclosure"] == main.KNOWLEDGE_DISCLOSURE
    assert response.headers["x-simorgh-ai-generated"] == "false"


def test_agents_do_not_emit_synthetic_model_fallbacks(monkeypatch):
    from agents.hakim import HakimAgent
    from agents.nazer import NazerAgent
    from agents.rahbar import RahbarAgent
    import agents.hakim as hakim
    import agents.nazer as nazer
    import agents.rahbar as rahbar

    monkeypatch.setattr(hakim, "generate", lambda *args, **kwargs: None)
    monkeypatch.setattr(nazer, "generate", lambda *args, **kwargs: None)
    monkeypatch.setattr(rahbar, "generate", lambda *args, **kwargs: None)

    assert HakimAgent().analyze("آزمون") is None
    assert NazerAgent().analyze("آزمون") is None
    assert RahbarAgent().suggest("آزمون") is None


def test_voice_endpoint_propagates_text_generation_provenance(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import main
    import core.voice_endpoint as voice_endpoint

    output = tmp_path / "out.wav"
    output.write_bytes(b"RIFF-test")

    monkeypatch.setattr(voice_endpoint, "transcribe", lambda path: "سلام")
    monkeypatch.setattr(
        voice_endpoint,
        "ask",
        lambda query, agent="hakim", return_metadata=False: (
            ("پاسخ محلی", False) if return_metadata else "پاسخ محلی"
        ),
    )
    monkeypatch.setattr(voice_endpoint, "synthesize", lambda text: str(output))

    client = TestClient(main.app)
    response = client.post(
        "/voice",
        content=b"0" * 1000,
        headers={
            "content-type": "application/octet-stream",
            "x-simorgh-session": "test-session",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-simorgh-ai-generated"] == "false"


def test_discover_backend_prefers_managed_port_over_stale_environment(monkeypatch, tmp_path):
    import json
    import core.local_backend as backend

    meta = tmp_path / "llama-server.json"
    meta.write_text(
        json.dumps(
            {
                "pid": 12345,
                "model": "/tmp/qwen.gguf",
                "port": 8081,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(backend, "BACKEND_META_FILE", meta)
    monkeypatch.setattr(backend, "_managed_pid", lambda: 12345)
    monkeypatch.setattr(backend, "_find_binary", lambda: "/tmp/llama-server")
    monkeypatch.setenv(
        "SIMORGH_LLM_FAST_URL",
        "http://127.0.0.1:8090/v1/chat/completions",
    )
    monkeypatch.setenv(
        "SIMORGH_LLM_FAST_MODELS_URL",
        "http://127.0.0.1:8090/v1/models",
    )

    seen = {}

    def fake_models_payload(url, timeout=1.5):
        seen["url"] = url
        return {"data": [{"id": "/tmp/qwen.gguf"}]}

    monkeypatch.setattr(backend, "_models_payload", fake_models_payload)

    result = backend.discover_backend()

    assert result["managed_port"] == 8081
    assert result["endpoint"] == "http://127.0.0.1:8081/v1/chat/completions"
    assert result["models_endpoint"] == "http://127.0.0.1:8081/v1/models"
    assert seen["url"] == "http://127.0.0.1:8081/v1/models"
    assert result["endpoint_up"] is True
    assert result["loaded_models"] == ["/tmp/qwen.gguf"]


def test_managed_backend_pid_is_accepted_when_process_identity_matches(monkeypatch, tmp_path):
    import json
    import core.local_backend as backend

    meta = tmp_path / "llama-server.json"
    meta.write_text(
        json.dumps(
            {
                "pid": 70998,
                "model": "/tmp/qwen.gguf",
                "port": 8089,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(backend, "BACKEND_PID_FILE", tmp_path / "llama-server.pid")
    backend.BACKEND_PID_FILE.write_text("70998", encoding="utf-8")
    monkeypatch.setattr(backend, "BACKEND_META_FILE", meta)
    monkeypatch.setattr(
        backend,
        "_process_cmdline",
        lambda pid: [
            "/home/mahdi/.local/share/simorgh/bin/llama-server",
            "--model",
            "/tmp/qwen.gguf",
            "--host",
            "127.0.0.1",
            "--port",
            "8089",
        ],
    )

    assert backend._managed_pid() == 70998
