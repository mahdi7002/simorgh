from __future__ import annotations

import json
import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.mother.ai_work_log import AIWorkLog
from core.mother.ai_work_log_api import router
from core.mother.ledger import MotherLedger


def test_ai_work_log_defaults_to_claimed(tmp_path):
    log = AIWorkLog(MotherLedger(tmp_path / "mother.db"))

    entry_id = log.record(
        actor="Claude",
        model="claude",
        repo="~/SimorghCore",
        ref="main",
        action="feature",
        summary="poetry lookup",
        reason="track today's work",
        evidence="file:data/poetry/EVIDENCE.md",
    )

    item = log.get(entry_id)
    assert item is not None
    assert item["verification"] == "claimed"
    assert item["verified_by"] is None


def test_ai_work_log_report_groups_by_actor(tmp_path):
    log = AIWorkLog(MotherLedger(tmp_path / "mother.db"))

    for actor in ("Claude", "Claude", "ChatGPT", "Gemma", "human"):
        log.record(
            actor=actor,
            model=None,
            repo=None,
            ref=None,
            action="test",
            summary="sample",
            reason=None,
            evidence="manual",
        )

    report = log.report()

    assert report["sample_count"] == 5
    assert report["by_actor"]["Claude"]["sample_count"] == 2
    assert report["by_actor"]["Claude"]["verification"]["claimed"]["sample_count"] == 2
    assert len(report["by_actor"]["Claude"]["entries"]) == 2


def test_ai_work_log_http_post_and_get(tmp_path, monkeypatch):
    replacement = AIWorkLog(MotherLedger(tmp_path / "mother.db"))
    monkeypatch.setattr(
        "core.mother.ai_work_log_api._work_log",
        replacement,
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/mother/ai-work-log",
        json={
            "actor": "Claude",
            "model": "claude",
            "repo": "~/SimorghCore",
            "ref": "main",
            "action": "feature",
            "summary": "poetry lookup",
            "reason": "track today's work",
            "evidence": json.dumps({"path": "data/poetry/EVIDENCE.md"}),
        },
    )

    assert response.status_code == 200
    assert response.json()["verification"] == "claimed"

    report = client.get("/api/mother/ai-work-log/report")

    assert report.status_code == 200
    body = report.json()
    assert body["sample_count"] == 1
    assert body["by_actor"]["Claude"]["sample_count"] == 1
    assert body["by_actor"]["Claude"]["entries"][0]["summary"] == "poetry lookup"


def test_ai_work_log_git_verification_requires_actor_contract(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    (repo / "file.txt").write_text("ok", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "test work\n\nAI-Actor: Claude",
        ],
        check=True,
    )

    log = AIWorkLog(MotherLedger(tmp_path / "mother.db"))
    entry_id = log.record(
        actor="Claude",
        model="claude",
        repo=str(repo),
        ref="HEAD",
        action="test",
        summary="reproducible commit",
        reason="test commit contract",
        evidence=json.dumps({"git_commit": {"repo": str(repo), "ref": "HEAD"}}),
    )

    result = log.verify_reproducible(entry_id)

    assert result["verification"] == "verified"
    assert result["verified_by"] == "Mother"
