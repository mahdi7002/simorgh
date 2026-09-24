from __future__ import annotations

from core.mother.service import MotherService


def test_health_state_reports_degraded_before_observer_runs():
    service = MotherService()
    state = service.health_state()
    assert state["status"] == "degraded"
    assert state["observer"] == "not_running"


def test_health_state_reports_healthy_after_observer_success(monkeypatch):
    service = MotherService()
    service._observer_alive = True
    service._last_observer_error = None

    state = service.health_state()

    assert state["status"] == "healthy"
    assert state["observer"] == "running"
    assert state["last_error"] is None
