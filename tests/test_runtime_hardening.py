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
