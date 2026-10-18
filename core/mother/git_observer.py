from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


class GitObserver:
    """Lightweight, read-mostly observer for the repository hosting Mother."""

    def __init__(
        self,
        repo_path: str | os.PathLike[str] | None = None,
        *,
        fetch_interval_seconds: int = 300,
        command_timeout_seconds: float = 8.0,
        size_measure_interval_seconds: int = 900,
    ) -> None:
        default_repo = Path(__file__).resolve().parents[2]
        self.repo_path = Path(
            repo_path
            or os.environ.get("SIMORGH_MOTHER_REPO")
            or default_repo
        ).expanduser().resolve()

        self.fetch_interval_seconds = max(30, int(fetch_interval_seconds))
        self.command_timeout_seconds = max(1.0, float(command_timeout_seconds))
        self.size_measure_interval_seconds = max(60, int(size_measure_interval_seconds))
        self._last_fetch_monotonic = 0.0
        self._last_size_measure_monotonic = 0.0
        self._cached_repository_bytes: int | None = None
        self._cached_git_storage_bytes: int | None = None

    def _run_git(
        self,
        *args: str,
        timeout: float | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), *args],
            capture_output=True,
            text=True,
            timeout=timeout or self.command_timeout_seconds,
            check=False,
        )

        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(detail or f"git exited {result.returncode}")

        return result

    def _git(self, *args: str, timeout: float | None = None) -> str:
        return self._run_git(*args, timeout=timeout).stdout.strip()

    def _try_git(self, *args: str, timeout: float | None = None) -> str | None:
        result = self._run_git(*args, timeout=timeout, check=False)
        if result.returncode != 0:
            return None

        value = result.stdout.strip()
        return value or None

    @staticmethod
    def _parse_status(output: str) -> dict[str, Any]:
        branch = None
        head = None
        upstream = None
        ahead = None
        behind = None

        modified = 0
        staged = 0
        unstaged = 0
        untracked = 0
        conflicts = 0
        changed_paths: list[str] = []

        for line in output.splitlines():
            if line.startswith("# branch.oid "):
                head = line[len("# branch.oid ") :].strip()

            elif line.startswith("# branch.head "):
                branch = line[len("# branch.head ") :].strip()

            elif line.startswith("# branch.upstream "):
                upstream = line[len("# branch.upstream ") :].strip()

            elif line.startswith("# branch.ab "):
                match = re.search(r"\+(\d+)\s+-(\d+)", line)
                if match:
                    ahead = int(match.group(1))
                    behind = int(match.group(2))

            elif line.startswith("1 ") or line.startswith("2 "):
                parts = line.split(" ", 8)
                xy = parts[1] if len(parts) > 1 else ".."

                modified += 1

                if xy[:1] not in {".", "?"}:
                    staged += 1

                if len(xy) > 1 and xy[1] not in {".", "?"}:
                    unstaged += 1

                if "U" in xy:
                    conflicts += 1

                if len(parts) >= 9:
                    changed_paths.append(parts[8])

            elif line.startswith("u "):
                parts = line.split(" ", 10)
                modified += 1
                conflicts += 1

                if len(parts) >= 11:
                    changed_paths.append(parts[10])

            elif line.startswith("? "):
                untracked += 1
                changed_paths.append(line[2:])

        return {
            "branch": branch,
            "head": head,
            "upstream": upstream,
            "ahead": ahead,
            "behind": behind,
            "modified": modified,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "conflicts": conflicts,
            "changed_paths": changed_paths[:250],
        }

    @staticmethod
    def _parse_shortstat(value: str | None) -> dict[str, int]:
        result = {
            "files": 0,
            "insertions": 0,
            "deletions": 0,
            "lines_changed": 0,
        }

        if not value:
            return result

        match = re.search(r"(\d+)\s+files?\s+changed", value)
        if match:
            result["files"] = int(match.group(1))

        match = re.search(r"(\d+)\s+insertions?\(\+\)", value)
        if match:
            result["insertions"] = int(match.group(1))

        match = re.search(r"(\d+)\s+deletions?\(-\)", value)
        if match:
            result["deletions"] = int(match.group(1))

        result["lines_changed"] = (
            result["insertions"] + result["deletions"]
        )

        return result

    @staticmethod
    def _path_size_bytes(path: Path) -> int | None:
        try:
            if path.is_file():
                return path.stat().st_size

            total = 0
            for item in path.rglob("*"):
                try:
                    if item.is_file():
                        total += item.stat().st_size
                except OSError:
                    continue

            return total
        except OSError:
            return None

    def _sync_state(
        self,
        *,
        dirty: bool,
        conflicts: int,
        upstream: str | None,
        ahead: int | None,
        behind: int | None,
        remote_fetch_status: str,
    ) -> str:
        if conflicts:
            return "SYNC_BLOCKED"

        if dirty:
            return "DIRTY"

        if not upstream:
            return "NO_UPSTREAM"

        if remote_fetch_status == "ERROR":
            return "REMOTE_UNKNOWN"

        if ahead == 0 and behind == 0:
            return "SYNCED"

        if ahead and ahead > 0 and behind == 0:
            return "LOCAL_AHEAD"

        if behind and behind > 0 and ahead == 0:
            return "REMOTE_AHEAD"

        if (ahead or 0) > 0 and (behind or 0) > 0:
            return "DIVERGED"

        return "SYNC_UNKNOWN"

    def _fetch_if_due(self) -> dict[str, Any]:
        now = time.monotonic()

        if now - self._last_fetch_monotonic < self.fetch_interval_seconds:
            return {
                "status": "SKIPPED",
                "reason": "cadence",
            }

        remote = self._try_git("remote", "get-url", "origin")

        if not remote:
            self._last_fetch_monotonic = now
            return {
                "status": "NOT_AVAILABLE",
                "reason": "origin_missing",
            }

        result = self._run_git(
            "fetch",
            "--prune",
            "--no-tags",
            "origin",
            timeout=max(10.0, self.command_timeout_seconds * 3),
            check=False,
        )

        self._last_fetch_monotonic = now

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[:1000]
            return {
                "status": "ERROR",
                "detail": detail,
            }

        return {"status": "OK"}

    def observe(self, *, fetch: bool = True) -> dict[str, Any]:
        observed_at = time.time()

        fetch_result = (
            self._fetch_if_due()
            if fetch
            else {"status": "SKIPPED", "reason": "disabled"}
        )

        try:
            root = Path(self._git("rev-parse", "--show-toplevel"))
            git_dir = self._git("rev-parse", "--git-dir")
            common_git_dir = self._git("rev-parse", "--git-common-dir")

            status_raw = self._git(
                "--no-optional-locks",
                "status",
                "--porcelain=v2",
                "--branch",
                "--ahead-behind",
            )
            status = self._parse_status(status_raw)

            upstream = status["upstream"]
            ahead = status["ahead"]
            behind = status["behind"]

            default_ref = self._try_git(
                "symbolic-ref",
                "--quiet",
                "refs/remotes/origin/HEAD",
            )

            if not default_ref and self._try_git(
                "rev-parse",
                "--verify",
                "origin/main",
            ):
                default_ref = "refs/remotes/origin/main"

            default_remote_head = None
            default_remote_ahead = None
            default_remote_behind = None

            if default_ref:
                default_remote_head = self._try_git(
                    "rev-parse",
                    default_ref,
                )

                comparison = self._try_git(
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"{default_ref}...HEAD",
                )

                if comparison:
                    left, right = comparison.split()
                    default_remote_behind = int(left)
                    default_remote_ahead = int(right)

            remote_url = self._try_git(
                "remote",
                "get-url",
                "origin",
            )

            dirty = bool(
                status["modified"]
                or status["untracked"]
                or status["staged"]
                or status["unstaged"]
            )

            working_diff = self._parse_shortstat(
                self._try_git("diff", "--shortstat")
            )

            staged_diff = self._parse_shortstat(
                self._try_git(
                    "diff",
                    "--cached",
                    "--shortstat",
                )
            )

            git_count_raw = self._try_git(
                "count-objects",
                "-vH",
            )

            git_count: dict[str, Any] = {}

            if git_count_raw:
                for line in git_count_raw.splitlines():
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        git_count[key] = value

            common_git_path = Path(common_git_dir)

            if not common_git_path.is_absolute():
                common_git_path = (
                    root / common_git_path
                ).resolve()

            now_monotonic = time.monotonic()
            if (
                self._cached_repository_bytes is None
                or self._cached_git_storage_bytes is None
                or now_monotonic - self._last_size_measure_monotonic
                >= self.size_measure_interval_seconds
            ):
                self._cached_repository_bytes = self._path_size_bytes(root)
                self._cached_git_storage_bytes = self._path_size_bytes(common_git_path)
                self._last_size_measure_monotonic = now_monotonic

            sync_state = self._sync_state(
                dirty=dirty,
                conflicts=status["conflicts"],
                upstream=upstream,
                ahead=ahead,
                behind=behind,
                remote_fetch_status=(
                    "ERROR"
                    if fetch_result.get("status") == "ERROR"
                    else "OK"
                ),
            )

            return {
                "status": "OK",
                "observed_at": observed_at,
                "repository": str(root),
                "remote": {
                    "name": "origin",
                    "url": remote_url,
                },
                "git_dir": git_dir,
                "git_common_dir": str(common_git_path),
                "branch": status["branch"],
                "head": status["head"],
                "upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "default_remote": {
                    "ref": default_ref,
                    "head": default_remote_head,
                    "ahead": default_remote_ahead,
                    "behind": default_remote_behind,
                },
                "dirty": dirty,
                "modified": status["modified"],
                "staged": status["staged"],
                "unstaged": status["unstaged"],
                "untracked": status["untracked"],
                "conflicts": status["conflicts"],
                "changed_paths": status["changed_paths"],
                "diff": {
                    "working_tree": working_diff,
                    "staged": staged_diff,
                    "lines_changed": (
                        working_diff["lines_changed"]
                        + staged_diff["lines_changed"]
                    ),
                },
                "storage": {
                    "repository_bytes": self._cached_repository_bytes,
                    "git_storage_bytes": self._cached_git_storage_bytes,
                    "size_cache": {
                        "interval_seconds": self.size_measure_interval_seconds,
                        "cached": True,
                    },
                    "count_objects": git_count,
                },
                "fetch": fetch_result,
                "sync_state": sync_state,
                "write_operations": [],
                "context_tokens": None,
                "context_status": "NOT_AVAILABLE",
            }

        except Exception as exc:
            return {
                "status": "ERROR",
                "observed_at": observed_at,
                "repository": str(self.repo_path),
                "sync_state": "SYNC_UNKNOWN",
                "write_operations": [],
                "error": {
                    "type": type(exc).__name__,
                    "detail": str(exc)[:1000],
                },
            }
