from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from core.user_runtime import DEFAULT_RUNTIME_DIR
except Exception:
    DEFAULT_RUNTIME_DIR = Path.home() / ".local" / "share" / "simorgh"

DB_PATH = Path(
    os.environ.get(
        "SIMORGH_AI_WORK_LOG_DB",
        str(DEFAULT_RUNTIME_DIR / "mother" / "ai_work_log.db"),
    )
).expanduser()

ALLOWED_ACTORS = {"Claude", "ChatGPT", "Gemma", "human"}
ALLOWED_VERIFICATION = {"claimed", "verified", "failed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_work_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                actor TEXT NOT NULL,
                model TEXT,
                repo TEXT,
                ref TEXT,
                action TEXT NOT NULL,
                summary TEXT NOT NULL,
                reason TEXT,
                evidence TEXT,
                verification TEXT NOT NULL DEFAULT 'claimed'
                    CHECK (verification IN ('claimed','verified','failed')),
                verified_by TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_work_log_actor_ts
            ON ai_work_log(actor, ts)
            """
        )


def record_claimed(
    *,
    actor: str,
    model: str | None,
    repo: str | None,
    ref: str | None,
    action: str,
    summary: str,
    reason: str | None,
    evidence: str | None,
) -> int:
    ensure_table()

    actor = actor.strip()
    if actor not in ALLOWED_ACTORS:
        raise ValueError(f"unsupported actor: {actor!r}")

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ai_work_log(
                ts, actor, model, repo, ref, action, summary,
                reason, evidence, verification, verified_by
            )
            VALUES(?,?,?,?,?,?,?,?,?,'claimed',NULL)
            """,
            (
                _now(),
                actor,
                model,
                repo,
                ref,
                action,
                summary,
                reason,
                evidence,
            ),
        )
        return int(cur.lastrowid)


def exists_claim(
    actor: str,
    action: str,
    summary: str,
) -> bool:
    ensure_table()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM ai_work_log
            WHERE actor=? AND action=? AND summary=?
            LIMIT 1
            """,
            (actor, action, summary),
        ).fetchone()
    return row is not None


def list_report(actor: str | None = None) -> dict[str, Any]:
    ensure_table()

    with connect() as conn:
        if actor:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_work_log
                WHERE actor=?
                ORDER BY id
                """,
                (actor,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_work_log
                ORDER BY id
                """
            ).fetchall()

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        grouped[item["actor"]].append(item)

    by_actor = {}
    for name in sorted(grouped):
        items = grouped[name]
        verification_counts = {
            status: sum(
                1 for item in items if item["verification"] == status
            )
            for status in sorted(ALLOWED_VERIFICATION)
        }
        by_actor[name] = {
            "sample_size": len(items),
            "verification_counts": verification_counts,
            "items": items,
        }

    return {
        "table": "ai_work_log",
        "db": str(DB_PATH),
        "sample_size": len(rows),
        "by_actor": by_actor,
        "note": (
            "Counts are sample sizes only. They are not quality scores "
            "and are not evidence of model superiority."
        ),
    }


def _git_commit_exists(repo: str, ref: str) -> bool:
    result = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result.returncode == 0


def _git_actor_marker(repo: str, ref: str, actor: str) -> bool:
    result = subprocess.run(
        ["git", "-C", repo, "log", "-1", "--format=%B", ref],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        return False

    marker = f"AI-Actor: {actor}"
    return marker in result.stdout


def verify_with_pytest(
    log_id: int,
    *,
    test_paths: list[str] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Mother-only verification path.

    A record becomes verified only when:
      1. repo/ref exist as a real git commit
      2. commit message contains AI-Actor: <actor>
      3. pytest exits with code 0

    Missing evidence leaves the record as claimed rather than inventing failure.
    """
    ensure_table()

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM ai_work_log WHERE id=?",
            (log_id,),
        ).fetchone()

    if row is None:
        raise KeyError(log_id)

    item = dict(row)
    repo = item.get("repo")
    ref = item.get("ref")
    actor = item.get("actor")

    if not repo or not ref:
        return {
            "status": "PENDING",
            "verification": "claimed",
            "reason": "missing_repo_or_ref",
        }

    if not Path(repo).is_dir() or not (Path(repo) / ".git").exists():
        return {
            "status": "PENDING",
            "verification": "claimed",
            "reason": "repo_not_available",
        }

    if not _git_commit_exists(repo, ref):
        return {
            "status": "PENDING",
            "verification": "claimed",
            "reason": "git_ref_not_reproducible",
        }

    if not _git_actor_marker(repo, ref, actor):
        with connect() as conn:
            conn.execute(
                """
                UPDATE ai_work_log
                SET verification='failed', verified_by='Mother'
                WHERE id=?
                """,
                (log_id,),
            )
        return {
            "status": "FAILED",
            "verification": "failed",
            "reason": "missing_AI_Actor_commit_marker",
        }

    command = [sys.executable, "-m", "pytest", "-q"]
    if test_paths:
        command.extend(test_paths)

    result = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode == 0:
        with connect() as conn:
            conn.execute(
                """
                UPDATE ai_work_log
                SET verification='verified', verified_by='Mother'
                WHERE id=?
                """,
                (log_id,),
            )
        return {
            "status": "VERIFIED",
            "verification": "verified",
            "verified_by": "Mother",
            "test_exit_code": result.returncode,
        }

    with connect() as conn:
        conn.execute(
            """
            UPDATE ai_work_log
            SET verification='failed', verified_by='Mother'
            WHERE id=?
            """,
            (log_id,),
        )

    return {
        "status": "FAILED",
        "verification": "failed",
        "verified_by": "Mother",
        "test_exit_code": result.returncode,
        "stderr_tail": result.stderr[-2000:],
    }


ensure_table()
