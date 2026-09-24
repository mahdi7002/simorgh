from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.user_runtime import DEFAULT_RUNTIME_DIR


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MotherLedger:
    """Append-oriented local ledger for boot, events, snapshots, reports and quarantine."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        self.db_path = Path(
            db_path
            or os.environ.get("SIMORGH_MOTHER_DB")
            or (DEFAULT_RUNTIME_DIR / "mother" / "mother.db")
        ).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boot_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    boot_id TEXT UNIQUE NOT NULL,
                    started_at TEXT NOT NULL,
                    previous_boot_id TEXT,
                    last_shutdown_at TEXT,
                    clean_shutdown INTEGER,
                    status TEXT NOT NULL DEFAULT 'running'
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    boot_id TEXT NOT NULL,
                    component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT,
                    severity TEXT NOT NULL DEFAULT 'info',
                    verified INTEGER NOT NULL DEFAULT 0,
                    provenance TEXT NOT NULL DEFAULT 'system_observation',
                    data_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_boot ON events(boot_id);
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    boot_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(timestamp);
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reports_type_time ON reports(report_type, created_at);
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    source TEXT NOT NULL DEFAULT 'human',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    target_date TEXT
                );
                CREATE TABLE IF NOT EXISTS quarantine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_domain TEXT NOT NULL,
                    title TEXT,
                    content_type TEXT,
                    content_sha256 TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'QUARANTINED',
                    ai_review_json TEXT,
                    human_review_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine(status);
                CREATE TABLE IF NOT EXISTS code_repairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    task TEXT NOT NULL,
                    patch TEXT,
                    status TEXT NOT NULL DEFAULT 'PROPOSED',
                    verification_json TEXT,
                    applied_commit TEXT
                );
                """
            )

    @staticmethod
    def boot_id() -> str:
        try:
            return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
        except OSError:
            return "boot-unknown"

    def begin_boot(self) -> dict[str, Any]:
        current = self.boot_id()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT boot_id, started_at, previous_boot_id, clean_shutdown, status "
                "FROM boot_sessions WHERE boot_id=?",
                (current,),
            ).fetchone()
            if row:
                return dict(row)

            previous = conn.execute(
                "SELECT boot_id, started_at, last_shutdown_at, clean_shutdown, status "
                "FROM boot_sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previous_id = previous["boot_id"] if previous else None
            conn.execute(
                "INSERT INTO boot_sessions(boot_id,started_at,previous_boot_id,clean_shutdown,status) "
                "VALUES(?,?,?,?,?)",
                (current, utc_now(), previous_id, None, "running"),
            )
        self.record_event(
            component="mother",
            event_type="boot_started",
            actor="mother",
            action="observe",
            severity="info",
            verified=True,
            data={
                "boot_id": current,
                "previous_boot_id": previous_id,
                "previous_clean_shutdown": previous["clean_shutdown"] if previous else None,
            },
        )
        return {
            "boot_id": current,
            "started_at": utc_now(),
            "previous_boot_id": previous_id,
            "previous_clean_shutdown": previous["clean_shutdown"] if previous else None,
            "previous_started_at": previous["started_at"] if previous else None,
            "previous_shutdown_at": previous["last_shutdown_at"] if previous else None,
        }

    def mark_shutdown(self, clean: bool = True) -> None:
        now = utc_now()
        current = self.boot_id()
        with self.connect() as conn:
            conn.execute(
                "UPDATE boot_sessions SET last_shutdown_at=?, clean_shutdown=?, status=? WHERE boot_id=?",
                (now, int(bool(clean)), "shutdown", current),
            )
        self.record_event(
            component="mother",
            event_type="shutdown",
            actor="mother",
            action="observe",
            severity="info" if clean else "warning",
            verified=True,
            data={"clean": bool(clean)},
        )

    def record_event(
        self,
        *,
        component: str,
        event_type: str,
        actor: str,
        action: str | None = None,
        severity: str = "info",
        verified: bool = False,
        provenance: str = "system_observation",
        data: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        payload = data or {}
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO events(event_id,timestamp,boot_id,component,event_type,actor,action,"
                "severity,verified,provenance,data_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    timestamp or utc_now(),
                    self.boot_id(),
                    component,
                    event_type,
                    actor,
                    action,
                    severity,
                    int(bool(verified)),
                    provenance,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
                ),
            )
        return event_id

    def latest_event(self, event_type: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM events WHERE event_type=? ORDER BY timestamp DESC LIMIT 1",
                (event_type,),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["data"] = json.loads(item.pop("data_json"))
        return item

    def events_for_boot(self, boot_id: str, limit: int = 5000) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE boot_id=? ORDER BY timestamp LIMIT ?",
                (boot_id, max(1, min(int(limit), 10000))),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item.pop("data_json"))
            result.append(item)
        return result

    def save_snapshot(self, snapshot: dict[str, Any]) -> int:
        raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO snapshots(timestamp,boot_id,sha256,payload_json) VALUES(?,?,?,?)",
                (snapshot.get("timestamp", utc_now()), snapshot.get("boot_id", self.boot_id()), digest, raw),
            )
            return int(cur.lastrowid)

    def latest_snapshot(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT timestamp,boot_id,sha256,payload_json FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return {}
        data = json.loads(row["payload_json"])
        data["_ledger"] = {"timestamp": row["timestamp"], "boot_id": row["boot_id"], "sha256": row["sha256"]}
        return data

    def snapshots_since(self, timestamp: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT timestamp,boot_id,sha256,payload_json FROM snapshots WHERE timestamp>=? ORDER BY id",
                (timestamp,),
            ).fetchall()
        return [
            {
                **json.loads(row["payload_json"]),
                "_ledger": {
                    "timestamp": row["timestamp"],
                    "boot_id": row["boot_id"],
                    "sha256": row["sha256"],
                },
            }
            for row in rows
        ]

    def events_between(self, start: str, end: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events WHERE timestamp>=?"
        params: list[Any] = [start]
        if end:
            sql += " AND timestamp<=?"
            params.append(end)
        sql += " ORDER BY timestamp LIMIT ?"
        params.append(int(limit))
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item.pop("data_json"))
            result.append(item)
        return result

    def save_report(self, report_type: str, period_start: str, period_end: str, payload: dict[str, Any]) -> int:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO reports(report_type,period_start,period_end,created_at,sha256,payload_json)"
                " VALUES(?,?,?,?,?,?)",
                (report_type, period_start, period_end, utc_now(), digest, raw),
            )
            return int(cur.lastrowid)

    def latest_report(self, report_type: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT report_type,period_start,period_end,created_at,sha256,payload_json "
                "FROM reports WHERE report_type=? ORDER BY id DESC LIMIT 1",
                (report_type,),
            ).fetchone()
        if not row:
            return {}
        payload = json.loads(row["payload_json"])
        payload["_ledger"] = {
            "report_type": row["report_type"],
            "period_start": row["period_start"],
            "period_end": row["period_end"],
            "created_at": row["created_at"],
            "sha256": row["sha256"],
        }
        return payload

    def list_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id,report_type,period_start,period_end,created_at,sha256,payload_json "
                "FROM reports ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "report_type": row["report_type"],
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "created_at": row["created_at"],
                "sha256": row["sha256"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def add_goal(self, title: str, target_date: str | None = None, source: str = "human") -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO goals(title,status,source,created_at,updated_at,target_date) VALUES(?,?,?,?,?,?)",
                (title.strip(), "OPEN", source, now, now, target_date),
            )
            return int(cur.lastrowid)

    def list_goals(self, status: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM goals"
        params: list[Any] = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY updated_at DESC"
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def set_goal_status(self, goal_id: int, status: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE goals SET status=?,updated_at=? WHERE id=?",
                (status, utc_now(), int(goal_id)),
            )
            return cur.rowcount == 1

    def add_quarantine(
        self,
        *,
        source_url: str,
        source_domain: str,
        title: str | None,
        content_type: str | None,
        content: str,
        ai_review: dict[str, Any] | None = None,
    ) -> int:
        now = utc_now()
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO quarantine(created_at,updated_at,source_url,source_domain,title,"
                "content_type,content_sha256,content,status,ai_review_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    now,
                    now,
                    source_url,
                    source_domain,
                    title,
                    content_type,
                    digest,
                    content,
                    "QUARANTINED",
                    json.dumps(ai_review, ensure_ascii=False, sort_keys=True) if ai_review else None,
                ),
            )
            return int(cur.lastrowid)

    def get_quarantine(self, item_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM quarantine WHERE id=?", (int(item_id),)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["ai_review"] = json.loads(item.pop("ai_review_json")) if item["ai_review_json"] else None
        item["human_review"] = json.loads(item.pop("human_review_json")) if item["human_review_json"] else None
        return item

    def list_quarantine(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        sql = "SELECT id,created_at,updated_at,source_url,source_domain,title,content_type,content_sha256,status,"
        sql += "ai_review_json,human_review_json FROM quarantine"
        params: list[Any] = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(int(limit), 100)))
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["ai_review"] = json.loads(item.pop("ai_review_json")) if item["ai_review_json"] else None
            item["human_review"] = json.loads(item.pop("human_review_json")) if item["human_review_json"] else None
            result.append(item)
        return result

    def approve_quarantine(self, item_id: int, review: dict[str, Any]) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE quarantine SET status='APPROVED',updated_at=?,human_review_json=? "
                "WHERE id=? AND status='QUARANTINED'",
                (utc_now(), json.dumps(review, ensure_ascii=False, sort_keys=True), int(item_id)),
            )
            return cur.rowcount == 1

    def reject_quarantine(self, item_id: int, review: dict[str, Any]) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE quarantine SET status='REJECTED',updated_at=?,human_review_json=? "
                "WHERE id=? AND status='QUARANTINED'",
                (utc_now(), json.dumps(review, ensure_ascii=False, sort_keys=True), int(item_id)),
            )
            return cur.rowcount == 1

    def create_code_repair(self, task: str, patch: str | None) -> int:
        now = utc_now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO code_repairs(created_at,updated_at,task,patch,status) VALUES(?,?,?,?,?)",
                (now, now, task, patch, "PROPOSED"),
            )
            return int(cur.lastrowid)

    def update_code_repair(self, repair_id: int, *, status: str, verification: dict[str, Any] | None = None,
                           applied_commit: str | None = None) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE code_repairs SET updated_at=?,status=?,verification_json=?,applied_commit=? WHERE id=?",
                (
                    utc_now(),
                    status,
                    json.dumps(verification, ensure_ascii=False, sort_keys=True) if verification else None,
                    applied_commit,
                    int(repair_id),
                ),
            )
            return cur.rowcount == 1

    def get_code_repair(self, repair_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM code_repairs WHERE id=?", (int(repair_id),)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["verification"] = json.loads(item.pop("verification_json")) if item["verification_json"] else None
        return item


    def list_code_repairs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id,created_at,updated_at,task,status,verification_json,applied_commit "
                "FROM code_repairs ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["verification"] = (
                json.loads(item.pop("verification_json"))
                if item["verification_json"]
                else None
            )
            result.append(item)
        return result
