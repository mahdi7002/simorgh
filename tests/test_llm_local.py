from __future__ import annotations

from core import llm_local


def test_report_budget_allows_real_context_window_case():
    from core.mother.context_governor import budget_for

    budget = budget_for(
        n_ctx=4096,
        input_tokens=1700,
        requested_output=128,
        task_class="report",
    )

    assert budget["status"] == "ALLOW"
    assert budget["within_budget"] is True
    assert budget["input_ceiling"] == 2048


def test_local_llm_timeout_defaults_are_suitable_for_cpu_models(monkeypatch):
    monkeypatch.delenv("SIMORGH_FAST_TIMEOUT", raising=False)
    monkeypatch.delenv("SIMORGH_QUALITY_TIMEOUT", raising=False)

    import importlib

    importlib.reload(llm_local)

    assert llm_local.FAST_TIMEOUT == 60.0
    assert llm_local.QUALITY_TIMEOUT == 120.0


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

    monkeypatch.setattr(llm_local, "_prepare_offline_first", lambda: None)

    monkeypatch.setattr(
        llm_local,
        "discover_local_brain",
        lambda: {
            "backend": "llama.cpp",
            "base_url": "http://127.0.0.1:8081",
            "model": "test-model",
            "n_ctx": 4096,
            "n_ctx_train": 131072,
            "status": "READY",
        },
    )

    monkeypatch.setattr(
        llm_local,
        "count_input_tokens",
        lambda *args, **kwargs: 10,
    )

    monkeypatch.setattr(llm_local.requests, "post", fake_post)

    monkeypatch.setenv(
        "SIMORGH_LLM_QUALITY_URL",
        "http://127.0.0.1:8081/v1/chat/completions",
    )

    monkeypatch.setattr(llm_local, "QUALITY_TIMEOUT", 120.0)

    result = llm_local.generate(
        "system",
        "user",
        needs_quality=True,
    )

    assert result == "پاسخ"
    assert captured["timeout"] == 120.0


def test_offline_first_selects_running_loopback_model(monkeypatch):
    monkeypatch.setenv("SIMORGH_PRIVACY_MODE", "local-only")
    monkeypatch.setenv(
        "SIMORGH_LLM_QUALITY_URL",
        "http://127.0.0.1:8081/v1/chat/completions",
    )
    monkeypatch.setenv(
        "SIMORGH_LLM_QUALITY_MODELS_URL",
        "http://127.0.0.1:8081/v1/models",
    )
    monkeypatch.setenv(
        "SIMORGH_LLM_FAST_URL",
        "http://127.0.0.1:8080/v1/chat/completions",
    )
    monkeypatch.setenv(
        "SIMORGH_LLM_FAST_MODELS_URL",
        "http://127.0.0.1:8080/v1/models",
    )

    def fake_prepare():
        monkeypatch.setenv(
            "SIMORGH_LLM_QUALITY_URL",
            "http://127.0.0.1:8080/v1/chat/completions",
        )
        monkeypatch.setenv(
            "SIMORGH_LLM_QUALITY_MODELS_URL",
            "http://127.0.0.1:8080/v1/models",
        )
        return {
            "status": "READY",
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
            "models_endpoint": "http://127.0.0.1:8080/v1/models",
            "models": ["gemma-3-4b-it-qat-Q4_0.gguf"],
        }

    import importlib

    importlib.reload(llm_local)
    monkeypatch.setattr(
        "core.mother.local_model.prepare_local_model_environment",
        fake_prepare,
    )

    llm_local._LAST_LOCAL_PREPARE = 0.0
    llm_local._prepare_offline_first()

    assert llm_local._quality_url() == "http://127.0.0.1:8080/v1/chat/completions"
    assert llm_local._quality_models_url() == "http://127.0.0.1:8080/v1/models"

def test_report_uses_report_timeout(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "گزارش"}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["timeout"] = kwargs["timeout"]
        return FakeResponse()

    monkeypatch.setattr(
        llm_local,
        "_prepare_offline_first",
        lambda: None,
    )

    monkeypatch.setattr(
        llm_local,
        "discover_local_brain",
        lambda: {
            "backend": "llama.cpp",
            "base_url": "http://127.0.0.1:8080",
            "model": "test-model",
            "n_ctx": 4096,
            "n_ctx_train": 131072,
            "status": "READY",
        },
    )

    monkeypatch.setattr(
        llm_local,
        "count_input_tokens",
        lambda *args, **kwargs: 100,
    )

    monkeypatch.setattr(
        llm_local.requests,
        "post",
        fake_post,
    )

    monkeypatch.setattr(
        llm_local,
        "REPORT_TIMEOUT",
        180.0,
    )

    result = llm_local.generate(
        "system",
        "user",
        max_tokens=32,
        needs_quality=True,
        task_class="report",
    )

    assert result == "گزارش"
    assert captured["timeout"] == 180.0

