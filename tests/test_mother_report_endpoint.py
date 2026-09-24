from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.mother.api as mother_api


def test_report_ask_returns_local_model_response(monkeypatch):
    app = FastAPI()
    app.include_router(mother_api.router)
    client = TestClient(app)

    reports = {
        "DAILY": {
            "report_type": "DAILY",
            "events_total": 3,
            "changes": ["cpu.percent: 10 → 20"],
            "latest_quality_check": {"status": "OK"},
        },
        "WEEKLY": None,
        "POST_BOOT": {"report_type": "POST_BOOT", "offline_interval_seconds": 12.0},
    }

    monkeypatch.setattr(
        mother_api.ledger,
        "latest_report",
        lambda report_type: reports.get(report_type),
    )
    monkeypatch.setattr(
        mother_api.ledger,
        "latest_snapshot",
        lambda: {
            "timestamp": "2026-09-25T00:00:00+00:00",
            "cpu": {"percent": 20},
            "memory": {"percent": 55},
            "swap": {"percent": 10},
        },
    )
    monkeypatch.setattr(mother_api.ledger, "list_goals", lambda: [])
    monkeypatch.setattr(mother_api.ledger, "list_self_model", lambda: [])

    captured = {}

    def fake_generate(system_prompt, user_message, max_tokens=350, needs_quality=False):
        captured["system_prompt"] = system_prompt
        captured["user_message"] = user_message
        captured["max_tokens"] = max_tokens
        captured["needs_quality"] = needs_quality
        return "گزارش تولیدشده توسط Gemma"

    monkeypatch.setattr(mother_api, "generate", fake_generate)

    response = client.post("/api/mother/report/ask")

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "گزارش تولیدشده توسط Gemma"
    assert body["ai_generated"] is True
    assert body["model_mode"] == "local-only"
    assert body["evidence_scope"] == "mother_local_state"
    assert captured["needs_quality"] is True
    assert captured["max_tokens"] == 650
    assert "گزارش و مشاهدهٔ واقعی محلی" in captured["user_message"]


def test_report_ask_returns_503_when_local_model_unavailable(monkeypatch):
    app = FastAPI()
    app.include_router(mother_api.router)
    client = TestClient(app)

    monkeypatch.setattr(
        mother_api.ledger,
        "latest_report",
        lambda kind: {"report_type": kind},
    )
    monkeypatch.setattr(
        mother_api.ledger,
        "latest_snapshot",
        lambda: {"timestamp": "2026-09-25T00:00:00+00:00"},
    )
    monkeypatch.setattr(mother_api.ledger, "list_goals", lambda: [])
    monkeypatch.setattr(mother_api.ledger, "list_self_model", lambda: [])
    monkeypatch.setattr(
        mother_api,
        "generate",
        lambda *args, **kwargs: None,
    )

    response = client.post("/api/mother/report/ask")

    assert response.status_code == 503
    assert response.json()["detail"] == "local model unavailable"
