from __future__ import annotations

import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.stdout


def test_workspace_inspector_contract(tmp_path):
    from core.mother.workspace_inspector import WorkspaceInspector

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text("{}", encoding="utf-8")
    state = WorkspaceInspector().inspect([repo])
    assert state["repository_count"] == 1
    assert "node" in state["repositories"][0]["contract"]["contracts"]
    assert "package.json" in state["repositories"][0]["contract"]["marker_files"]


def test_workspace_capsule_restores_tracked_staged_unstaged_and_untracked(tmp_path):
    from core.mother.workspace_capsule import create_capsule, restore_capsule

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "mother@test.local")
    git(repo, "config", "user.name", "Mother Test")

    tracked = repo / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "initial", "-q")

    tracked.write_text("two-staged\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    tracked.write_text("two-staged-and-unstaged\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("hello\n", encoding="utf-8")

    capsule = create_capsule([repo], tmp_path / "capsule")
    restored_root = tmp_path / "restored"
    restored = restore_capsule(capsule, restored_root)
    restored_repo = restored[0]

    assert (restored_repo / "tracked.txt").read_text(encoding="utf-8") == "two-staged-and-unstaged\n"
    assert (restored_repo / "untracked.txt").read_text(encoding="utf-8") == "hello\n"
    cached = git(restored_repo, "diff", "--cached", "--", "tracked.txt")
    assert "two-staged" in cached


def test_workspace_cli_inspect_local(tmp_path, capsys):
    from core.mother.workspace_cli import main

    repo = tmp_path / "repo"
    repo.mkdir()
    assert main(["inspect", str(repo)]) == 0
    output = capsys.readouterr().out
    assert "SIMORGH_MOTHER_WORKSPACE_V1" in output


def test_workspace_capsule_preserves_staged_and_unstaged_same_file(tmp_path):
    from core.mother.workspace_capsule import create_capsule, restore_capsule

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "mother@test.local")
    git(repo, "config", "user.name", "Mother Test")

    tracked = repo / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "initial", "-q")

    tracked.write_text("two-staged\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    tracked.write_text("two-staged-and-unstaged\n", encoding="utf-8")

    capsule = create_capsule([repo], tmp_path / "capsule")
    restored = restore_capsule(capsule, tmp_path / "restored")[0]

    assert (restored / "tracked.txt").read_text(encoding="utf-8") == "two-staged-and-unstaged\n"
    cached = git(restored, "diff", "--cached", "--", "tracked.txt")
    assert "two-staged" in cached
    unstaged = git(restored, "diff", "--", "tracked.txt")
    assert "two-staged-and-unstaged" in unstaged


def test_project_auditor_detects_without_execution(tmp_path):
    from core.mother.project_auditor import audit_project

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / "tests").mkdir()

    result = audit_project(repo, execute=False)

    assert result["health"] == "NOT_RUN"
    assert result["contract"]["contracts"] == ["python"]
    assert result["checks"][0]["kind"] == "python-test"
    assert result["checks"][0]["status"] == "NOT_RUN"


def test_project_auditor_executes_passing_python_test(tmp_path):
    from core.mother.project_auditor import audit_project

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_ok():\n    assert 2 + 2 == 4\n", encoding="utf-8")

    result = audit_project(repo, execute=True, timeout=30)

    assert result["health"] == "PASS"
    assert result["checks"][0]["status"] == "PASS"
