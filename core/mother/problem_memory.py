from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class ProblemMemory:
    """Persistent, local-only operational memory for incidents and verified lessons."""

    _shared: "ProblemMemory | None" = None

    def __init__(self, db_path: str | Path | None = None) -> None:
        env_path = os.environ.get("SIMORGH_MOTHER_DB")
        self.db_path = Path(db_path or env_path or (Path.home() / ".local/share/simorgh/mother/mother.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def shared(cls, db_path: str | Path | None = None) -> "ProblemMemory":
        if cls._shared is None:
            cls._shared = cls(db_path)
        return cls._shared

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): ProblemMemory._redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ProblemMemory._redact(v) for v in value]
        if not isinstance(value, str):
            return value
        patterns = [
            (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,]+", r"\1[REDACTED]"),
            (r"(?i)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,]+", r"\1[REDACTED]"),
        ]
        result = value
        for pattern, repl in patterns:
            result = re.sub(pattern, repl, result)
        return result[:12000]

    @classmethod
    def _json(cls, value: Any) -> str:
        cleaned = cls._redact(value)
        return json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)[:20000]

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def fingerprint(cls, component: str, failure_type: str, signature: Any) -> str:
        canonical = cls._json(signature)
        return cls._hash(f"{component.strip()}|{failure_type.strip()}|{canonical}")[:32]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=2.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=2000")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS mother_problem_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    component TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_by TEXT NOT NULL,
                    symptom TEXT,
                    signature_json TEXT,
                    evidence_json TEXT,
                    evidence_sha256 TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    occurrence_count INTEGER NOT NULL DEFAULT 1,
                    resolved_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mpi_fp ON mother_problem_incidents(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_mpi_status ON mother_problem_incidents(status);
                CREATE INDEX IF NOT EXISTS idx_mpi_component_type ON mother_problem_incidents(component, failure_type);

                CREATE TABLE IF NOT EXISTS mother_problem_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT,
                    method TEXT NOT NULL,
                    action TEXT,
                    command TEXT,
                    result TEXT,
                    success INTEGER,
                    verified INTEGER NOT NULL DEFAULT 0,
                    evidence_json TEXT,
                    evidence_sha256 TEXT,
                    error TEXT,
                    duration_ms REAL,
                    FOREIGN KEY (incident_id) REFERENCES mother_problem_incidents(incident_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_mpa_incident ON mother_problem_attempts(incident_id, attempted_at);

                CREATE TABLE IF NOT EXISTS mother_problem_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    attempt_id INTEGER,
                    verified_at TEXT NOT NULL,
                    verifier_type TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    useful INTEGER NOT NULL DEFAULT 0,
                    evidence_json TEXT,
                    evidence_sha256 TEXT,
                    notes TEXT,
                    FOREIGN KEY (incident_id) REFERENCES mother_problem_incidents(incident_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_mpv_incident ON mother_problem_verifications(incident_id, verified_at);

                CREATE TABLE IF NOT EXISTS mother_problem_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_key TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    component TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    signature_json TEXT,
                    method TEXT NOT NULL,
                    action TEXT,
                    actor_type TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    verification_count INTEGER NOT NULL DEFAULT 0,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    confidence_label TEXT NOT NULL DEFAULT 'LOW',
                    evidence_json TEXT,
                    last_verified_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mpl_fp ON mother_problem_lessons(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_mpl_component_type ON mother_problem_lessons(component, failure_type);
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(mother_problem_incidents)").fetchall()}
            if "cause_json" not in columns:
                conn.execute("ALTER TABLE mother_problem_incidents ADD COLUMN cause_json TEXT")

    def record_incident(
        self,
        *,
        component: str,
        failure_type: str,
        severity: str,
        detected_by: str,
        symptom: str | None = None,
        signature: Any = None,
        evidence: Any = None,
    ) -> dict[str, Any]:
        now = self._now()
        signature = {} if signature is None else signature
        fingerprint = self.fingerprint(component, failure_type, signature)
        evidence_json = self._json(evidence or {})
        evidence_sha = self._hash(evidence_json)
        cls_symptom = self._redact(symptom) if symptom else None

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mother_problem_incidents WHERE fingerprint=? AND status IN ('OPEN','RESOLVED_PENDING_VERIFICATION') ORDER BY id DESC LIMIT 1",
                (fingerprint,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE mother_problem_incidents SET last_seen=?, occurrence_count=occurrence_count+1, severity=?, symptom=?, evidence_json=?, evidence_sha256=?, updated_at=? WHERE incident_id=?",
                    (now, severity, cls_symptom, evidence_json, evidence_sha, now, row["incident_id"]),
                )
                incident_id = row["incident_id"]
                created = False
            else:
                incident_id = "INC-" + now.replace("-", "").replace(":", "").replace("+00:00", "") + "-" + fingerprint[:10]
                conn.execute(
                    "INSERT INTO mother_problem_incidents (incident_id,fingerprint,component,failure_type,severity,status,detected_by,symptom,signature_json,evidence_json,evidence_sha256,first_seen,last_seen,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        incident_id, fingerprint, component, failure_type, severity, "OPEN", detected_by,
                        cls_symptom, self._json(signature), evidence_json, evidence_sha, now, now, now, now,
                    ),
                )
                created = True

        return {"incident_id": incident_id, "fingerprint": fingerprint, "created": created}

    def record_attempt(
        self,
        incident_id: str,
        *,
        actor_type: str,
        method: str,
        action: str | None = None,
        command: str | None = None,
        result: str | None = None,
        success: bool | None = None,
        verified: bool = False,
        evidence: Any = None,
        error: str | None = None,
        duration_ms: float | None = None,
        kind: str = "attempt",
    ) -> dict[str, Any]:
        now = self._now()
        evidence_json = self._json(evidence or {})
        with self._connect() as conn:
            exists = conn.execute("SELECT incident_id FROM mother_problem_incidents WHERE incident_id=?", (incident_id,)).fetchone()
            if not exists:
                raise KeyError(f"unknown incident: {incident_id}")
            cur = conn.execute(
                "INSERT INTO mother_problem_attempts (incident_id,kind,attempted_at,actor_type,actor_id,method,action,command,result,success,verified,evidence_json,evidence_sha256,error,duration_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    incident_id, kind, now, actor_type, None, method, action,
                    self._redact(command) if command else None, result,
                    None if success is None else int(success), int(verified), evidence_json,
                    self._hash(evidence_json), self._redact(error) if error else None, duration_ms,
                ),
            )
            attempt_id = int(cur.lastrowid)
            incident = conn.execute("SELECT * FROM mother_problem_incidents WHERE incident_id=?", (incident_id,)).fetchone()
            if incident is not None and success is False:
                attempt = conn.execute("SELECT * FROM mother_problem_attempts WHERE id=?", (attempt_id,)).fetchone()
                if attempt is not None:
                    self._record_method_failure(conn, incident, attempt, now)
            if kind == "resolution":
                conn.execute(
                    "UPDATE mother_problem_incidents SET status='RESOLVED_PENDING_VERIFICATION', resolved_at=?, updated_at=? WHERE incident_id=? AND status='OPEN'",
                    (now, now, incident_id),
                )
        return {"incident_id": incident_id, "attempt_id": attempt_id, "kind": kind}

    def _record_method_failure(self, conn: sqlite3.Connection, incident: sqlite3.Row, attempt: sqlite3.Row, now: str) -> None:
        lesson_key = self._hash(f"{incident['fingerprint']}|{attempt['method']}|{attempt['action'] or ''}")[:32]
        row = conn.execute("SELECT * FROM mother_problem_lessons WHERE lesson_key=?", (lesson_key,)).fetchone()
        if not row:
            return
        success_count = row["success_count"]
        failure_count = row["failure_count"] + 1
        confidence = (success_count + 1.0) / (success_count + failure_count + 2.0)
        label = "HIGH" if success_count >= 3 and confidence >= 0.80 else ("MEDIUM" if success_count >= 2 and confidence >= 0.65 else "LOW")
        conn.execute(
            "UPDATE mother_problem_lessons SET failure_count=?,confidence=?,confidence_label=?,updated_at=? WHERE lesson_key=?",
            (failure_count, confidence, label, now, lesson_key),
        )

    def verify_resolution(
        self,
        incident_id: str,
        *,
        verifier_type: str,
        verified: bool,
        useful: bool = False,
        evidence: Any = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        now = self._now()
        evidence_json = self._json(evidence or {})
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mother_problem_incidents WHERE incident_id=?", (incident_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"unknown incident: {incident_id}")
            latest = conn.execute(
                "SELECT * FROM mother_problem_attempts WHERE incident_id=? AND kind='resolution' ORDER BY id DESC LIMIT 1",
                (incident_id,),
            ).fetchone()
            cur = conn.execute(
                "INSERT INTO mother_problem_verifications (incident_id,attempt_id,verified_at,verifier_type,verified,useful,evidence_json,evidence_sha256,notes) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    incident_id, latest["id"] if latest else None, now, verifier_type,
                    int(verified), int(useful), evidence_json, self._hash(evidence_json), notes,
                ),
            )
            verification_id = int(cur.lastrowid)
            if verified:
                conn.execute(
                    "UPDATE mother_problem_incidents SET status='VERIFIED_RESOLVED', resolved_at=COALESCE(resolved_at,?), updated_at=? WHERE incident_id=?",
                    (now, now, incident_id),
                )
                if latest:
                    conn.execute("UPDATE mother_problem_attempts SET verified=1 WHERE id=?", (latest["id"],))
                if useful:
                    self._learn_from_resolution(conn, row, latest, evidence_json, now)
            else:
                conn.execute(
                    "UPDATE mother_problem_incidents SET status='RESOLVED_UNVERIFIED', updated_at=? WHERE incident_id=?",
                    (now, incident_id),
                )
        return {"incident_id": incident_id, "verification_id": verification_id, "verified": verified, "useful": useful}

    def _learn_from_resolution(self, conn: sqlite3.Connection, incident: sqlite3.Row, attempt: sqlite3.Row | None, evidence_json: str, now: str) -> None:
        if not attempt:
            return
        method = attempt["method"]
        action = attempt["action"]
        lesson_key = self._hash(f"{incident['fingerprint']}|{method}|{action or ''}")[:32]
        old = conn.execute("SELECT * FROM mother_problem_lessons WHERE lesson_key=?", (lesson_key,)).fetchone()
        if old:
            success_count = old["success_count"] + 1
            failure_count = old["failure_count"]
            verification_count = old["verification_count"] + 1
            use_count = old["use_count"]
            component = old["component"]
            failure_type = old["failure_type"]
            signature_json = old["signature_json"]
            actor_type = old["actor_type"]
            created_at = old["created_at"]
        else:
            success_count = 1
            failure_count = 0
            verification_count = 1
            use_count = 0
            component = incident["component"]
            failure_type = incident["failure_type"]
            signature_json = incident["signature_json"]
            actor_type = attempt["actor_type"]
            created_at = now
        confidence = (success_count + 1.0) / (success_count + failure_count + 2.0)
        label = "HIGH" if success_count >= 3 and confidence >= 0.80 else ("MEDIUM" if success_count >= 2 and confidence >= 0.65 else "LOW")
        if old:
            conn.execute(
                "UPDATE mother_problem_lessons SET success_count=?,verification_count=?,confidence=?,confidence_label=?,evidence_json=?,last_verified_at=?,updated_at=? WHERE lesson_key=?",
                (success_count, verification_count, confidence, label, evidence_json, now, now, lesson_key),
            )
        else:
            conn.execute(
                "INSERT INTO mother_problem_lessons (lesson_key,fingerprint,component,failure_type,signature_json,method,action,actor_type,success_count,failure_count,verification_count,use_count,confidence,confidence_label,evidence_json,last_verified_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    lesson_key, incident["fingerprint"], component, failure_type, signature_json,
                    method, action, actor_type, success_count, failure_count, verification_count,
                    use_count, confidence, label, evidence_json, now, created_at, now,
                ),
            )

    def recover_by_signature(
        self,
        *,
        component: str,
        failure_type: str,
        signature: Any,
        verifier_type: str,
        evidence: Any,
        method: str = "deterministic state recovery",
        action: str = "state returned below threshold",
    ) -> list[dict[str, Any]]:
        fp = self.fingerprint(component, failure_type, signature)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT incident_id FROM mother_problem_incidents WHERE fingerprint=? AND status='OPEN' ORDER BY id DESC",
                (fp,),
            ).fetchall()
        results = []
        for row in rows:
            iid = row["incident_id"]
            resolution = self.record_attempt(
                iid, actor_type="deterministic", method=method, action=action,
                result="recovered", success=True, kind="resolution", evidence=evidence,
            )
            verification = self.verify_resolution(
                iid, verifier_type=verifier_type, verified=True, useful=True, evidence=evidence,
            )
            results.append({"incident_id": iid, "resolution": resolution, "verification": verification})
        return results

    def set_diagnosis(self, incident_id: str, *, cause: Any, basis: Any = None, diagnosed_by: str = "human") -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT incident_id FROM mother_problem_incidents WHERE incident_id=?",
                (incident_id,),
            ).fetchone()
            if not row:
                return False
            payload = self._json({
                "cause": cause,
                "basis": basis or {},
                "diagnosed_by": diagnosed_by,
            })
            conn.execute(
                "UPDATE mother_problem_incidents SET cause_json=?, updated_at=? WHERE incident_id=?",
                (payload, self._now(), incident_id),
            )
        return True

    def record_lesson_use(self, lesson_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM mother_problem_lessons WHERE id=?",
                (int(lesson_id),),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE mother_problem_lessons SET use_count=use_count+1, updated_at=? WHERE id=?",
                (self._now(), int(lesson_id)),
            )
        return True

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM mother_problem_incidents WHERE incident_id=?", (incident_id,)).fetchone()
            if not row:
                return None
            attempts = conn.execute("SELECT * FROM mother_problem_attempts WHERE incident_id=? ORDER BY id", (incident_id,)).fetchall()
            verifications = conn.execute("SELECT * FROM mother_problem_verifications WHERE incident_id=? ORDER BY id", (incident_id,)).fetchall()
        incident = dict(row)
        if incident.get("cause_json"):
            try:
                incident["cause"] = json.loads(incident["cause_json"])
            except json.JSONDecodeError:
                incident["cause"] = {"raw": incident["cause_json"]}
        return {
            "incident": incident,
            "attempts": [dict(r) for r in attempts],
            "verifications": [dict(r) for r in verifications],
        }

    def list_incidents(self, *, status: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self._connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM mother_problem_incidents WHERE status=? ORDER BY last_seen DESC LIMIT ?", (status, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM mother_problem_incidents ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def lessons(self, *, component: str | None = None, failure_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        clauses = []
        args: list[Any] = []
        if component:
            clauses.append("component=?")
            args.append(component)
        if failure_type:
            clauses.append("failure_type=?")
            args.append(failure_type)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM mother_problem_lessons{where} ORDER BY confidence DESC, success_count DESC, last_verified_at DESC LIMIT ?",
                [*args, limit],
            ).fetchall()
        return [dict(r) for r in rows]

    def suggestions(self, *, component: str, failure_type: str, signature: Any | None = None, limit: int = 3) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 10))
        exact_fp = self.fingerprint(component, failure_type, {} if signature is None else signature)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM mother_problem_lessons WHERE fingerprint=? ORDER BY confidence DESC, success_count DESC LIMIT ?",
                (exact_fp, limit),
            ).fetchall()
            if len(rows) < limit:
                more = conn.execute(
                    "SELECT * FROM mother_problem_lessons WHERE component=? AND failure_type=? AND fingerprint!=? ORDER BY confidence DESC, success_count DESC LIMIT ?",
                    (component, failure_type, exact_fp, limit - len(rows)),
                ).fetchall()
                rows = list(rows) + list(more)
        return [self._lesson_public(dict(r)) for r in rows]

    @staticmethod
    def _lesson_public(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "lesson_id": row["id"],
            "component": row["component"],
            "failure_type": row["failure_type"],
            "method": row["method"],
            "action": row["action"],
            "actor_type": row["actor_type"],
            "success_count": row["success_count"],
            "failure_count": row["failure_count"],
            "verification_count": row["verification_count"],
            "confidence": round(float(row["confidence"]), 3),
            "confidence_label": row["confidence_label"],
            "last_verified_at": row["last_verified_at"],
        }

    def context(self, *, limit: int = 3) -> dict[str, Any]:
        open_incidents = self.list_incidents(status="OPEN", limit=limit)
        items = []
        for inc in open_incidents:
            sig = json.loads(inc.get("signature_json") or "{}")
            items.append({
                "incident_id": inc["incident_id"],
                "component": inc["component"],
                "failure_type": inc["failure_type"],
                "severity": inc["severity"],
                "status": inc["status"],
                "occurrence_count": inc["occurrence_count"],
                "first_seen": inc["first_seen"],
                "last_seen": inc["last_seen"],
                "signature": sig,
                "known_solutions": self.suggestions(
                    component=inc["component"], failure_type=inc["failure_type"], signature=sig, limit=2,
                ),
            })
        return {
            "open_incidents": items,
            "principle": "Only VERIFIED_RESOLVED incidents create reusable lessons.",
        }

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            incidents = conn.execute("SELECT COUNT(*) FROM mother_problem_incidents").fetchone()[0]
            open_count = conn.execute("SELECT COUNT(*) FROM mother_problem_incidents WHERE status='OPEN'").fetchone()[0]
            lessons = conn.execute("SELECT COUNT(*) FROM mother_problem_lessons").fetchone()[0]
            verified = conn.execute("SELECT COUNT(*) FROM mother_problem_verifications WHERE verified=1").fetchone()[0]
        return {
            "incidents": int(incidents),
            "open_incidents": int(open_count),
            "lessons": int(lessons),
            "verified_resolutions": int(verified),
        }


if __name__ == "__main__":
    print(json.dumps({"db_path": str(ProblemMemory.shared().db_path), "stats": ProblemMemory.shared().stats(), "context": ProblemMemory.shared().context()}, ensure_ascii=False, indent=2))
