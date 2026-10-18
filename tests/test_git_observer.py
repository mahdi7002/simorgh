from __future__ import annotations

import subprocess

from core.mother.git_observer import GitObserver


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_parse_porcelain_v2_counts_dirty_state():
    output = """# branch.oid abc123
# branch.head feature-x
# branch.upstream origin/feature-x
# branch.ab +2 -3
1 .M N... 100644 100644 100644 aaa aaa file1.py
1 M. N... 100644 100644 100644 bbb bbb file2.py
? new.txt
"""

    state = GitObserver._parse_status(output)

    assert state["branch"] == "feature-x"
    assert state["head"] == "abc123"
    assert state["upstream"] == "origin/feature-x"
    assert state["ahead"] == 2
    assert state["behind"] == 3
    assert state["modified"] == 2
    assert state["staged"] == 1
    assert state["unstaged"] == 1
    assert state["untracked"] == 1
    assert set(state["changed_paths"]) == {
        "file1.py",
        "file2.py",
        "new.txt",
    }


def test_observe_local_repository_without_remote(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init", "-q")

    observer = GitObserver(
        repo,
        fetch_interval_seconds=300,
    )

    result = observer.observe(fetch=False)

    assert result["status"] == "OK"
    assert result["repository"] == str(repo.resolve())
    assert result["remote"]["url"] is None
    assert result["fetch"]["status"] == "SKIPPED"
    assert result["write_operations"] == []
    assert result["context_tokens"] is None


def test_observe_detects_untracked_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init", "-q")
    (repo / "example.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = GitObserver(repo).observe(fetch=False)

    assert result["status"] == "OK"
    assert result["dirty"] is True
    assert result["untracked"] == 1
    assert "example.txt" in result["changed_paths"]
    assert result["sync_state"] == "DIRTY"


def test_sync_state_never_requests_write_operation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init", "-q")

    result = GitObserver(repo).observe(fetch=False)

    assert result["write_operations"] == []
    assert "push" not in result["write_operations"]
    assert "pull" not in result["write_operations"]
    assert "reset" not in result["write_operations"]
    assert result["sync_state"] in {
        "NO_UPSTREAM",
        "SYNC_UNKNOWN",
    }


def test_shortstat_parser():
    parsed = GitObserver._parse_shortstat(
        "3 files changed, 10 insertions(+), 4 deletions(-)"
    )

    assert parsed == {
        "files": 3,
        "insertions": 10,
        "deletions": 4,
        "lines_changed": 14,
    }


def test_storage_measurement_is_cached(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    git(repo, "init", "-q")
    (repo / "example.txt").write_text("hello", encoding="utf-8")

    observer = GitObserver(
        repo,
        size_measure_interval_seconds=900,
    )

    calls = {"count": 0}
    original = observer._path_size_bytes

    def counted(path):
        calls["count"] += 1
        return original(path)

    monkeypatch.setattr(observer, "_path_size_bytes", counted)

    first = observer.observe(fetch=False)
    second = observer.observe(fetch=False)

    assert first["storage"]["repository_bytes"] is not None
    assert second["storage"]["repository_bytes"] == first["storage"]["repository_bytes"]

    # One scan for the working tree + one for the git storage on the first
    # observation. The second observation must use cached values.
    assert calls["count"] == 2
