from __future__ import annotations

from core.mother import local_model


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_local_model_prefers_running_loopback_endpoint(monkeypatch):
    seen = []

    def fake_get(url, timeout=2):
        seen.append(url)
        if url.endswith(":8081/v1/models"):
            return FakeResponse({"data": []})
        return FakeResponse({"data": [{"id": "gemma-local"}]})

    monkeypatch.delenv("SIMORGH_LLM_QUALITY_MODELS_URL", raising=False)
    monkeypatch.delenv("SIMORGH_LLM_FAST_MODELS_URL", raising=False)
    monkeypatch.setattr(local_model.requests, "get", fake_get)
    monkeypatch.setattr(
        "core.user_runtime.load_config",
        lambda: {"llm_quality_models_url": "http://127.0.0.1:8081/v1/models"},
    )

    result = local_model.prepare_local_model_environment()

    assert result["status"] == "READY"
    assert result["models"] == ["gemma-local"]
    assert result["endpoint"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert seen == [
        "http://127.0.0.1:8081/v1/models",
        "http://127.0.0.1:8080/v1/models",
    ]


def test_local_model_ignores_non_loopback_config(monkeypatch):
    def fake_get(url, timeout=2):
        assert "127.0.0.1:8080" in url
        return FakeResponse({"data": [{"id": "local"}]})

    monkeypatch.setattr(local_model.requests, "get", fake_get)
    monkeypatch.setattr(
        "core.user_runtime.load_config",
        lambda: {"llm_quality_models_url": "https://example.com/v1/models"},
    )

    result = local_model.prepare_local_model_environment()

    assert result["status"] == "READY"
    assert result["models"] == ["local"]
