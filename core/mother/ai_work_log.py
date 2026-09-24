from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .ledger import MotherLedger, utc_now

ACTORS = ("Claude", "ChatGPT", "Gemma", "human")
VERIFICATIONS = ("claimed", "verified", "failed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_work_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL CHECK(actor IN ('Claude','ChatGPT','Gemma','human')),
    model TEXT,
    repo TEXT,
    ref TEXT,
    action TEXT NOT NULL,
    summary TEXT NOT NULL,
    reason TEXT,
    evidence TEXT NOT NULL,
    verification TEXT NOT NULL DEFAULT 'claimed'
        CHECK(verification IN ('claimed','verified','failed')),
    verified_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_work_log_ts ON ai_work_log(ts);
CREATE INDEX IF NOT EXISTS idx_ai_work_log_actor ON ai_work_log(actor);
CREATE INDEX IF NOT EXISTS idx_ai_work_log_verification ON ai_work_log(verification);
"""


class AIWorkLog:
    """Append-only provenance log for AI/human work claims and verification."""

    def __init__(self, ledger: MotherLedger):
        self.ledger = ledger
        with self.ledger.connect() as conn:
            conn.executescript(SCHEMA)

    def record(
        self,
        *,
        actor: str,
        model: str | None,
        repo: str | None,
        ref: str | None,
        action: str,
        summary: str,
        reason: str | None,
        evidence: str,
    ) -> int:
        actor = actor.strip()
        if actor not in ACTORS:
            raise ValueError(f"actor must be one of: {', '.join(ACTORS)}")
        action = action.strip()
        summary = summary.strip()
        evidence = evidence.strip()
        if not action or not summary or not evidence:
            raise ValueError("action, summary and evidence are required")

        with self.ledger.connect() as conn:
            cur = conn.execute(
                "INSERT INTO ai_work_log("
                "ts,actor,model,repo,ref,action,summary,reason,evidence,verification,verified_by"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,NULL)",
                (
                    utc_now(),
                    actor,
                    model.strip() if isinstance(model, str) and model.strip() else None,
                    repo.strip() if isinstance(repo, str) and repo.strip() else None,
                    ref.strip() if isinstance(ref, str) and ref.strip() else None,
                    action,
                    summary,
                    reason.strip() if isinstance(reason, str) and reason.strip() else None,
                    evidence,
                    "claimed",
                ),
            )
            return int(cur.lastrowid)

    def list_entries(self, actor: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if actor is not None and actor not in ACTORS:
            raise ValueError(f"actor must be one of: {', '.join(ACTORS)}")

        sql = (
            "SELECT id,ts,actor,model,repo,ref,action,summary,reason,evidence,verification,verified_by "
            "FROM ai_work_log"
        )
        params: list[Any] = []
        if actor:
            sql += " WHERE actor=?"
            params.append(actor)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 500)))

        with self.ledger.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get(self, entry_id: int) -> dict[str, Any] | None:
        with self.ledger.connect() as conn:
            row = conn.execute(
                "SELECT id,ts,actor,model,repo,ref,action,summary,reason,evidence,verification,verified_by "
                "FROM ai_work_log WHERE id=?",
                (int(entry_id),),
            ).fetchone()
        return dict(row) if row else None

    def verify_reproducible(self, entry_id: int) -> dict[str, Any]:
        """Verify only evidence Mother can reproduce locally."""
        item = self.get(entry_id)
        if not item:
            raise KeyError("ai work log entry not found")

        try:
            evidence = json.loads(item["evidence"])
        except json.JSONDecodeError:
            evidence = None

        if not isinstance(evidence, dict):
            return self._set_verification(
                entry_id,
                "failed",
                {"status": "FAILED", "reason": "evidence is not structured JSON"},
                "Mother",
            )

        checks: list[dict[str, Any]] = []

        git_check = evidence.get("git_commit")
        if git_check:
            if not isinstance(git_check, dict):
                checks.append({
                    "kind": "git_commit",
                    "status": "FAILED",
                    "reason": "git_commit evidence must be an object",
                })
            else:
                repo = str(git_check.get("repo") or item.get("repo") or "").strip()
                ref = str(git_check.get("ref") or item.get("ref") or "").strip()
                checks.append(self._verify_git_commit(repo, ref, item["actor"]))

        pytest_check = evidence.get("pytest")
        if pytest_check:
            checks.append(self._verify_pytest(pytest_check))

        if not checks:
            return self._set_verification(
                entry_id,
                "failed",
                {"status": "FAILED", "reason": "no supported reproducible evidence"},
                "Mother",
            )

        ok = all(check.get("status") == "VERIFIED" for check in checks)
        return self._set_verification(
            entry_id,
            "verified" if ok else "failed",
            {
                "status": "VERIFIED" if ok else "FAILED",
                "checks": checks,
                "verified_at": utc_now(),
            },
            "Mother",
        )

    @staticmethod
    def _verify_git_commit(repo: str, ref: str, actor: str) -> dict[str, Any]:
        if not repo or not ref or ref.startswith("-"):
            return {
                "kind": "git_commit",
                "status": "FAILED",
                "reason": "repo/ref missing or unsafe",
            }

        repo_path = Path(repo).expanduser()
        try:
            commit = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", f"{ref}^{{commit}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if commit.returncode != 0:
                return {
                    "kind": "git_commit",
                    "status": "FAILED",
                    "reason": "ref is not a resolvable commit",
                    "stderr": commit.stderr[-1000:],
                }

            message = subprocess.run(
                ["git", "-C", str(repo_path), "show", "-s", "--format=%B", ref],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            contract = f"AI-Actor: {actor}"
            if message.returncode != 0:
                return {
                    "kind": "git_commit",
                    "status": "FAILED",
                    "reason": "could not read commit message",
                }
            if contract not in message.stdout.splitlines():
                return {
                    "kind": "git_commit",
                    "status": "FAILED",
                    "reason": f"missing commit contract: {contract}",
                }

            return {
                "kind": "git_commit",
                "status": "VERIFIED",
                "repo": str(repo_path),
                "ref": ref,
                "commit": commit.stdout.strip(),
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "kind": "git_commit",
                "status": "FAILED",
                "reason": type(exc).__name__,
            }

    @staticmethod
    def _verify_pytest(test: Any) -> dict[str, Any]:
        if not isinstance(test, dict):
            return {
                "kind": "pytest",
                "status": "FAILED",
                "reason": "pytest evidence must be an object",
            }

        repo = Path(str(test.get("repo") or "")).expanduser()
        command = test.get("command")
        allowed = {
            ("pytest", "-q"),
            ("python3", "-m", "pytest", "-q"),
            ("python", "-m", "pytest", "-q"),
        }
        normalized = tuple(command) if isinstance(command, list) else None
        if not repo or normalized not in allowed:
            return {
                "kind": "pytest",
                "status": "FAILED",
                "reason": "only fixed pytest commands are reproducible",
            }

        try:
            result = subprocess.run(
                list(normalized),
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            return {
                "kind": "pytest",
                "status": "VERIFIED" if result.returncode == 0 else "FAILED",
                "repo": str(repo),
                "command": list(normalized),
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "kind": "pytest",
                "status": "FAILED",
                "reason": type(exc).__name__,
            }

    def _set_verification(
        self,
        entry_id: int,
        verification: str,
        details: dict[str, Any],
        verified_by: str,
    ) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            conn.execute(
                "UPDATE ai_work_log SET verification=?,verified_by=? WHERE id=?",
                (verification, verified_by, int(entry_id)),
            )
        result = self.get(entry_id) or {}
        result["verification_details"] = details
        return result

    def report(self) -> dict[str, Any]:
        with self.ledger.connect() as conn:
            rows = conn.execute(
                "SELECT id,ts,actor,model,repo,ref,action,summary,reason,evidence,verification,verified_by "
                "FROM ai_work_log ORDER BY id"
            ).fetchall()

        by_actor: dict[str, dict[str, Any]] = {}
        for actor in ACTORS:
            actor_rows = [row for row in rows if row["actor"] == actor]
            sample_count = len(actor_rows)
            verification_counts = Counter(row["verification"] for row in actor_rows)
            models = sorted({row["model"] for row in actor_rows if row["model"]})
            actions = sorted({row["action"] for row in actor_rows if row["action"]})

            entries = [dict(row) for row in actor_rows]
            by_actor[actor] = {
                "sample_count": sample_count,
                "verification": {
                    state: {
                        "value": verification_counts.get(state, 0),
                        "sample_count": sample_count,
                    }
                    for state in VERIFICATIONS
                },
                "verification_rate": {
                    "value": (
                        round(verification_counts.get("verified", 0) / sample_count, 4)
                        if sample_count
                        else None
                    ),
                    "sample_count": sample_count,
                },
                "models": models,
                "actions": actions,
                "entries": entries,
            }

        return {
            "sample_count": len(rows),
            "by_actor": by_actor,
            "note": "Numeric aggregates are descriptive only; each aggregate carries its sample_count.",
        }


__all__ = ["AIWorkLog", "ACTORS", "VERIFICATIONS"]
