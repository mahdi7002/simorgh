from __future__ import annotations

from core.mother.service import MotherService


def test_health_state_reports_degraded_before_observer_runs():
    service = MotherService()
    state = service.health_state()
    assert state["status"] == "degraded"
    assert state["observer"] == "not_running"


def test_health_state_reports_healthy_after_observer_success():
    service = MotherService()
    service._observer_alive = True
    service._last_observer_error = None

    state = service.health_state()

    assert state["status"] == "healthy"
    assert state["observer"] == "running"
    assert state["last_error"] is None


def test_mother_service_observes_multiple_repositories(tmp_path, monkeypatch):
    from core.mother.service import MotherService
    from core.mother.git_observer import GitObserver

    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    def fake_observe(self, fetch=True):
        return {
            "status": "OK",
            "repository": str(self.repo_path),
            "branch": "main",
            "head": "abc123",
            "sync_state": "CLEAN",
        }

    monkeypatch.setattr(GitObserver, "observe", fake_observe)

    service = MotherService(
        repositories=[repo1, repo2],
    )

    state = service._observe_git_repositories(fetch=False)

    assert state["status"] == "OK"
    assert state["aggregate_status"] == "OK"
    assert state["repository_count"] == 2
    assert [item["repository"] for item in state["repositories"]] == [
        str(repo1.resolve()),
        str(repo2.resolve()),
    ]

    # Backward compatibility: the first repository still provides
    # the historical top-level Git fields.
    assert state["repository"] == str(repo1.resolve())
    assert state["branch"] == "main"


def test_repository_config_is_loaded_and_deduplicated(tmp_path):
    import json

    from core.mother.repository_config import resolve_repository_paths

    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    config = tmp_path / "mother_repositories.json"
    config.write_text(
        json.dumps(
            {
                "repositories": [
                    str(repo1),
                    str(repo2),
                    str(repo1),
                ]
            }
        ),
        encoding="utf-8",
    )

    result = resolve_repository_paths(config_path=config)

    assert result == [
        repo1.resolve(),
        repo2.resolve(),
    ]


def test_invalid_git_repository_degrades_workspace(tmp_path, monkeypatch):
    from core.mother.service import MotherService
    from core.mother.git_observer import GitObserver

    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    def fake_observe(self, fetch=True):
        if self.repo_path == repo2.resolve():
            return {
                "status": "ERROR",
                "repository": str(self.repo_path),
                "sync_state": "SYNC_UNKNOWN",
                "error": {
                    "type": "RuntimeError",
                    "detail": "fatal: not a git repository (or any of the parent directories): .git",
                },
            }

        return {
            "status": "OK",
            "repository": str(self.repo_path),
            "branch": "main",
            "head": "abc123",
            "sync_state": "CLEAN",
        }

    monkeypatch.setattr(GitObserver, "observe", fake_observe)

    service = MotherService(
        repositories=[repo1, repo2],
    )

    state = service._observe_git_repositories(fetch=False)

    assert state["repository_count"] == 2
    assert state["aggregate_status"] == "DEGRADED"
    assert state["invalid_repository_indexes"] == [1]
    assert state["fatal_error_indexes"] == []


def test_unexpected_git_error_is_workspace_error(tmp_path, monkeypatch):
    from core.mother.service import MotherService
    from core.mother.git_observer import GitObserver

    repo = tmp_path / "repo"
    repo.mkdir()

    def fake_observe(self, fetch=True):
        return {
            "status": "ERROR",
            "repository": str(self.repo_path),
            "sync_state": "SYNC_UNKNOWN",
            "error": {
                "type": "RuntimeError",
                "detail": "git command timed out",
            },
        }

    monkeypatch.setattr(GitObserver, "observe", fake_observe)

    service = MotherService(
        repositories=[repo],
    )

    state = service._observe_git_repositories(fetch=False)

    assert state["aggregate_status"] == "ERROR"
    assert state["invalid_repository_indexes"] == []
    assert state["fatal_error_indexes"] == [0]


def test_workspace_inspector_is_part_of_mother_snapshot(tmp_path):
    from core.mother.service import MotherService

    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "mother@test.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Mother Test"], check=True)
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial", "-q"], check=True)

    service = MotherService(repositories=[repo])
    snapshot = service.observe_once()

    workspace = snapshot["workspace"]
    assert workspace["schema_version"] == "SIMORGH_MOTHER_WORKSPACE_V1"
    assert workspace["repository_count"] == 1
    assert workspace["repositories"][0]["path"] == str(repo.resolve())
    assert "python-pyproject" in workspace["repositories"][0]["contract"]["contracts"]
