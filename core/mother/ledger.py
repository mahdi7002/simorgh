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


MAX_REPORT_BYTES = 4_000_000


def compact_report_payload(value: Any, str_max: int = 2000, list_max: int = 100, _depth: int = 0) -> Any:
    """Bound the stored size of a report. Reports are views; complete events stay in the events table."""
    if _depth > 20:
        return "[COMPACTED_DEEP]"
    if isinstance(value, str):
        if len(value) > str_max:
            return value[:str_max] + f"...[COMPACTED_STR original_len={len(value)}]"
        return value
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for k, v in value.items():
            out[k] = compact_report_payload(v, str_max, list_max, _depth + 1)
            if isinstance(v, (list, tuple)) and len(v) > list_max:
                out[f"{k}__compacted_omitted"] = len(v) - list_max
        return out
    if isinstance(value, (list, tuple)):
        return [compact_report_payload(v, str_max, list_max, _depth + 1) for v in list(value)[:list_max]]
    return value


REPORT_KEEP_DAYS = 7
REPORT_MAX_TOTAL_BYTES = 1_000_000_000
REPORT_PRUNE_MAX_DB_BYTES = 5_000_000_000
REPORT_DIGEST_SQL = (
    "CREATE TABLE IF NOT EXISTS report_digests ("
    "report_id INTEGER PRIMARY KEY, report_type TEXT NOT NULL, period_start TEXT, period_end TEXT, "
    "created_at TEXT, sha256 TEXT, payload_bytes INTEGER, pruned_at TEXT NOT NULL)"
)


def select_reports_to_prune(rows, cutoff_iso, max_total_bytes):
    """rows: (id, report_type, created_at, nbytes). The newest row of each type is always kept.
    Rows newer than cutoff_iso are kept unless their total exceeds max_total_bytes (then only the newest per type stays)."""
    rows = list(rows)
    newest: dict[Any, int] = {}
    for rid, rtype, _created, _nbytes in rows:
        if rtype not in newest or rid > newest[rtype]:
            newest[rtype] = rid
    protected = set(newest.values())
    keep = {rid for rid, _t, created, _b in rows if created >= cutoff_iso} | protected
    total = sum((nbytes or 0) for rid, _t, _c, nbytes in rows if rid in keep)
    if total > max_total_bytes:
        keep = set(protected)
    return sorted(rid for rid, _t, _c, _b in rows if rid not in keep)


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
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

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
                CREATE TABLE IF NOT EXISTS self_model (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'KNOWN',
                    observed_at TEXT NOT NULL
                );
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
            try:
                conn.execute(
                    "INSERT INTO boot_sessions(boot_id,started_at,previous_boot_id,clean_shutdown,status) "
                    "VALUES(?,?,?,?,?)",
                    (current, utc_now(), previous_id, None, "running"),
                )
            except sqlite3.IntegrityError:
                # Race: another instance (orphan or overlapping restart) inserted
                # this boot_id between our SELECT and INSERT. Not fatal — the row
                # exists now, just re-read it instead of crashing the observer thread.
                row = conn.execute(
                    "SELECT boot_id, started_at, previous_boot_id, clean_shutdown, status "
                    "FROM boot_sessions WHERE boot_id=?",
                    (current,),
                ).fetchone()
                if row:
                    return dict(row)
                raise
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
        # Database invariant: events.provenance is NOT NULL.
        # Normalize an explicit None before the SQLite INSERT.
        if provenance is None:
            provenance = "system_observation"

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

    def _save_report_core(self, report_type: str, period_start: str, period_end: str, payload: dict[str, Any]) -> int:
        payload = compact_report_payload(payload)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        if len(raw) > MAX_REPORT_BYTES:
            payload = compact_report_payload(payload, str_max=400, list_max=20)
            raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        with self.connect() as conn:
            # DAILY/WEEKLY are refreshed views of a period, not append-only events.
            # Reuse the newest row for the same period to avoid storing a full growing
            # activity list every 15 minutes. POST_BOOT remains append-only: each boot
            # has its own history record. Existing duplicate rows are not deleted.
            if report_type in {"DAILY", "WEEKLY"}:
                if report_type == "WEEKLY":
                    # WEEKLY period_start slides with "now"; key it by the UTC day of period_end instead.
                    existing = conn.execute(
                        "SELECT id FROM reports WHERE report_type=? AND substr(period_end,1,10)=substr(?,1,10) ORDER BY id DESC LIMIT 1",
                        (report_type, period_end),
                    ).fetchone()
                else:
                    existing = conn.execute(
                        "SELECT id FROM reports WHERE report_type=? AND period_start=? ORDER BY id DESC LIMIT 1",
                        (report_type, period_start),
                    ).fetchone()
                if existing is not None:
                    report_id = int(existing[0])
                    conn.execute(
                        "UPDATE reports SET period_end=?,sha256=?,payload_json=? WHERE id=?",
                        (period_end, digest, raw, report_id),
                    )
                    return report_id

            cur = conn.execute(
                "INSERT INTO reports(report_type,period_start,period_end,created_at,sha256,payload_json)"
                " VALUES(?,?,?,?,?,?)",
                (report_type, period_start, period_end, utc_now(), digest, raw),
            )
            return int(cur.lastrowid)

    _last_prune_at: float | None = None

    def save_report(self, report_type: str, period_start: str, period_end: str, payload: dict[str, Any]) -> int:
        report_id = self._save_report_core(report_type, period_start, period_end, payload)
        try:
            self.prune_reports_if_due()
        except Exception as exc:  # retention must never break reporting
            import logging as _logging
            _logging.getLogger(__name__).warning("report prune skipped: %s: %s", type(exc).__name__, exc)
        return report_id

    def prune_reports_if_due(self, force: bool = False) -> dict[str, Any] | None:
        """Deterministic retention (no LLM): keep newest report per type + last REPORT_KEEP_DAYS days,
        keep a metadata digest of every deleted report. Raw facts stay in events/snapshots."""
        import logging as _logging
        import time as _time
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        now_m = _time.monotonic()
        if not force and MotherLedger._last_prune_at is not None and now_m - MotherLedger._last_prune_at < 3600:
            return None
        MotherLedger._last_prune_at = now_m
        log = _logging.getLogger(__name__)
        with self.connect() as conn:
            size = int(conn.execute("PRAGMA page_count").fetchone()[0]) * int(conn.execute("PRAGMA page_size").fetchone()[0])
            if size > REPORT_PRUNE_MAX_DB_BYTES:
                log.warning("report prune skipped: db is %.1f GB; run the offline rebuild", size / 1e9)
                return {"skipped": "db_too_large", "db_bytes": size}
            conn.execute(REPORT_DIGEST_SQL)
            rows = conn.execute(
                "SELECT id, report_type, period_start, period_end, created_at, sha256, length(CAST(payload_json AS BLOB)) FROM reports"
            ).fetchall()
            cutoff = (_dt.now(_tz.utc) - _td(days=REPORT_KEEP_DAYS)).isoformat()
            doomed = select_reports_to_prune(((r[0], r[1], r[4], r[6]) for r in rows), cutoff, REPORT_MAX_TOTAL_BYTES)
            if not doomed:
                return {"deleted": 0}
            by_id = {r[0]: r for r in rows}
            pruned_at = _dt.now(_tz.utc).isoformat()
            freed = 0
            for rid in doomed:
                r = by_id[rid]
                conn.execute(
                    "INSERT OR IGNORE INTO report_digests(report_id,report_type,period_start,period_end,created_at,sha256,payload_bytes,pruned_at)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (r[0], r[1], r[2], r[3], r[4], r[5], r[6], pruned_at),
                )
                conn.execute("DELETE FROM reports WHERE id=?", (rid,))
                freed += int(r[6] or 0)
            conn.commit()
            if int(conn.execute("PRAGMA auto_vacuum").fetchone()[0]) == 2:
                conn.execute("PRAGMA incremental_vacuum(50000)").fetchall()
        log.warning("reports pruned: deleted=%d freed_bytes=%d", len(doomed), freed)
        return {"deleted": len(doomed), "freed_bytes": freed}

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


    def set_self_fact(self, key: str, value: Any, *, source: str, status: str = "KNOWN") -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO self_model(key,value_json,source,status,observed_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,source=excluded.source,"
                "status=excluded.status,observed_at=excluded.observed_at",
                (key, json.dumps(value, ensure_ascii=False, sort_keys=True, default=str), source, status, utc_now()),
            )

    def record_capability(self, key: str, status: str, evidence: str,
                           source: str = "human_verified") -> None:
        """ثبت دستی وضعیت یک قابلیت با شواهد، جدا از observer خودکار سیستم."""
        import json, datetime
        value = json.dumps({"status": status, "evidence": evidence}, ensure_ascii=False)
        with self.connect() as c:
            c.execute(
                "INSERT INTO self_model(key,value_json,source,status,observed_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, source=excluded.source, "
                "status=excluded.status, observed_at=excluded.observed_at",
                (key, value, source, status, datetime.datetime.utcnow().isoformat() + "Z"),
            )

    def list_self_model(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT key,value_json,source,status,observed_at FROM self_model ORDER BY key"
            ).fetchall()
        return [
            {
                "key": row["key"],
                "value": json.loads(row["value_json"]),
                "source": row["source"],
                "status": row["status"],
                "observed_at": row["observed_at"],
            }
            for row in rows
        ]

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

# SIMORGH_BILINGUAL_LEDGER_BRIDGE_V1
# Bilingual narration is a sidecar. It does not replace or alter ledger facts.
try:
    from .bilingual_activity import install_ledger_bridge
    install_ledger_bridge(MotherLedger)
except Exception:
    # Mother must remain bootable even if narration storage has a problem.
    pass

