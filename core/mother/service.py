from __future__ import annotations

import signal
import time
from datetime import datetime, timezone
from typing import Any

from .ledger import MotherLedger
from .observer import SystemObserver
from .reports import ReportEngine
from .quality import run_daily_quality_check


class MotherService:
    """Long-lived, non-networked observer. It owns no port and never mutates source code."""

    def __init__(self, interval_seconds: int = 300):
        self.interval_seconds = max(30, int(interval_seconds))
        self.ledger = MotherLedger()
        self.observer = SystemObserver()
        self.reports = ReportEngine(self.ledger)
        self._stop = False
        self._last_observation = None
        self._observer_alive = False
        self._last_observer_error: dict[str, Any] | None = None

    def _handle_signal(self, signum, _frame) -> None:
        if signum in {signal.SIGTERM, signal.SIGINT}:
            self._stop = True

    @staticmethod
    def _changed(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        prev_units = (previous.get("systemd") or {}).get("units", {})
        cur_units = (current.get("systemd") or {}).get("units", {})
        for name in sorted(set(prev_units) | set(cur_units)):
            a = prev_units.get(name)
            b = cur_units.get(name)
            if a != b and (a or b):
                changes.append({"unit": name, "before": a, "after": b})
        for section, keys in {
            "cpu": ("percent",),
            "memory": ("percent", "available_mb"),
            "swap": ("percent",),
            "disk": ("percent", "free_gb"),
        }.items():
            a = previous.get(section, {})
            b = current.get(section, {})
            for key in keys:
                if a.get(key) != b.get(key):
                    changes.append({"metric": f"{section}.{key}", "before": a.get(key), "after": b.get(key)})
        return changes[:250]

    def _write_world_state(self, snapshot: dict[str, Any]) -> None:
        from pathlib import Path
        import json
        target = Path(snapshot.get("mother_dir") or self.ledger.db_path.parent) / "world_state.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": snapshot.get("timestamp"),
            "boot_id": snapshot.get("boot_id"),
            "snapshot": snapshot,
            "daily": self.ledger.latest_report("DAILY"),
            "weekly": self.ledger.latest_report("WEEKLY"),
            "post_boot": self.ledger.latest_report("POST_BOOT"),
            "goals": self.ledger.list_goals(),
        }
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp.replace(target)

    def _update_self_model(self, snapshot: dict[str, Any]) -> None:
        self.ledger.set_self_fact(
            "mother.identity",
            "SIMORGH MOTHER",
            source="mother_static",
        )
        self.ledger.set_self_fact(
            "mother.capability.observation",
            True,
            source="system_observer",
        )
        self.ledger.set_self_fact(
            "mother.capability.persistent_ledger",
            True,
            source="mother_ledger",
        )
        self.ledger.set_self_fact(
            "mother.boot_id",
            snapshot.get("boot_id"),
            source="kernel_boot_id",
        )
        self.ledger.set_self_fact(
            "mother.host",
            snapshot.get("host"),
            source="system_observer",
        )
        self.ledger.set_self_fact(
            "mother.python",
            snapshot.get("os", {}).get("python"),
            source="system_observer",
        )
        self.ledger.set_self_fact(
            "mother.cpu_threads",
            snapshot.get("cpu", {}).get("logical"),
            source="system_observer",
        )
        self.ledger.set_self_fact(
            "mother.process_count",
            snapshot.get("processes", {}).get("total_count"),
            source="system_observer",
        )
        self.ledger.set_self_fact(
            "mother.journal_readable",
            snapshot.get("access", {}).get("journal_readable"),
            source="system_observer",
            status="KNOWN" if snapshot.get("access", {}).get("journal_readable") else "NOT_AVAILABLE",
        )
        self.ledger.set_self_fact(
            "mother.user_repositories",
            snapshot.get("repositories", {}),
            source="git_observer",
        )

    def observe_once(self) -> dict[str, Any]:
        previous = self.ledger.latest_snapshot()
        journal = (
            self.observer.journal_since(previous.get("timestamp"))
            if previous
            else self.observer.journal_current_boot()
        )
        if journal.get("status") == "OK" and journal.get("lines"):
            self.ledger.record_event(
                component="system",
                event_type="journal_activity",
                actor="journalctl",
                action="observe",
                severity="info",
                verified=True,
                provenance="system_journal",
                data=journal,
            )
        elif journal.get("status") != "OK":
            self.ledger.record_event(
                component="system",
                event_type="journal_unavailable",
                actor="journalctl",
                action="observe",
                severity="warning",
                verified=False,
                data=journal,
            )
        snapshot = self.observer.capture()
        self.ledger.save_snapshot(snapshot)
        self._update_self_model(snapshot)
        self._write_world_state(snapshot)
        if previous:
            changes = self._changed(previous, snapshot)
            if changes:
                self.ledger.record_event(
                    component="mother",
                    event_type="state_changed",
                    actor="mother",
                    action="compare",
                    severity="info",
                    verified=True,
                    data={"changes": changes},
                )
        self._last_observation = snapshot
        return snapshot

    def start(self) -> None:
        boot = self.ledger.begin_boot()
        self.ledger.record_event(
            component="mother",
            event_type="observer_started",
            actor="mother",
            action="start",
            severity="info",
            verified=True,
            data={"interval_seconds": self.interval_seconds},
        )
        try:
            self.observe_once()
            self._observer_alive = True
            self._last_observer_error = None
        except Exception as exc:
            self._record_observer_error(exc)

        self.reports.post_boot(boot)
        self.reports.daily(with_ai=True)
        latest_snapshot = self.ledger.latest_snapshot()
        if latest_snapshot:
            self._write_world_state(latest_snapshot)
        last_daily_refresh = time.monotonic()
        last_weekly_refresh = time.monotonic()
        last_quality_check = time.monotonic()

        while not self._stop:
            now = time.monotonic()
            try:
                self.observe_once()
                self._observer_alive = True
                self._last_observer_error = None
                # Refresh the current-day report repeatedly so it always
                # represents activity up to the latest observation.
                if now - last_daily_refresh >= 900:
                    self.reports.daily(with_ai=False)
                    last_daily_refresh = now
                local_now = datetime.now().astimezone()
                latest_weekly = self.ledger.latest_report("WEEKLY")
                latest_weekly_date = latest_weekly.get("_ledger", {}).get("created_at", "")[:10]
                if local_now.weekday() == 6 and latest_weekly_date != local_now.date().isoformat():
                    self.reports.weekly(with_ai=True)
                    last_weekly_refresh = now
                if now - last_quality_check >= 86400:
                    run_daily_quality_check(self.ledger)
                    last_quality_check = now
            except Exception as exc:
                self._record_observer_error(exc)
            self._sleep_interruptibly()

        self.ledger.mark_shutdown(clean=True)

    def health_state(self) -> dict[str, Any]:
        if self._observer_alive:
            return {"status": "healthy", "observer": "running", "last_error": self._last_observer_error}
        return {"status": "degraded", "observer": "not_running", "last_error": self._last_observer_error}

    def _record_observer_error(self, exc: Exception) -> None:
        self._observer_alive = False
        self._last_observer_error = {"type": type(exc).__name__, "detail": str(exc)[:1000]}
        self.ledger.record_event(
            component="mother",
            event_type="observer_error",
            actor="mother",
            action="observe",
            severity="error",
            verified=False,
            data=self._last_observer_error,
        )

    def _sleep_interruptibly(self) -> None:
        deadline = time.monotonic() + self.interval_seconds
        while not self._stop and time.monotonic() < deadline:
            time.sleep(min(5, max(0.1, deadline - time.monotonic())))


def run() -> None:
    service = MotherService()
    signal.signal(signal.SIGTERM, service._handle_signal)
    signal.signal(signal.SIGINT, service._handle_signal)
    service.start()


if __name__ == "__main__":
    run()
