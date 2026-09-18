from __future__ import annotations

from core import llm_local


def test_local_llm_timeout_defaults_are_suitable_for_cpu_models(monkeypatch):
    monkeypatch.delenv("SIMORGH_FAST_TIMEOUT", raising=False)
    monkeypatch.delenv("SIMORGH_QUALITY_TIMEOUT", raising=False)

    import importlib

    importlib.reload(llm_local)

    assert llm_local.FAST_TIMEOUT == 30.0
    assert llm_local.QUALITY_TIMEOUT == 60.0


def test_generate_uses_quality_timeout(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "پاسخ"}}]}

    def fake_post(url, *, json, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(llm_local.requests, "post", fake_post)
    monkeypatch.setenv("SIMORGH_LLM_QUALITY_URL", "http://127.0.0.1:8081/v1/chat/completions")
    monkeypatch.setattr(llm_local, "QUALITY_TIMEOUT", 60.0)

    result = llm_local.generate("system", "user", needs_quality=True)

    assert result == "پاسخ"
    assert captured["url"] == "http://127.0.0.1:8081/v1/chat/completions"
    assert captured["timeout"] == 60.0
