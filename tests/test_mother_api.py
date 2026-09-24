from __future__ import annotations

from fastapi.testclient import TestClient

import main


def test_mother_console_route_exists():
    client = TestClient(main.app)
    response = client.get("/mother/")
    assert response.status_code == 200
    assert "مادر سیمرغ" in response.text


def test_mother_state_route_exists():
    client = TestClient(main.app)
    response = client.get("/api/mother/state")
    assert response.status_code == 200
    payload = response.json()
    assert "boot" in payload
    assert "snapshot" in payload
    assert "goals" in payload


def test_mother_code_apply_requires_verified_patch(monkeypatch):
    class FakeLedger:
        def get_code_repair(self, _):
            return {"id": 1, "verification": {"status": "FAILED"}, "patch": "diff"}

    from core.mother import api
    monkeypatch.setattr(api, "apply_verified_patch", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("only a VERIFIED patch can be applied")))
    response = TestClient(main.app).post(
        "/api/mother/coding/1/apply",
        json={"approve": True},
    )
    assert response.status_code == 400
