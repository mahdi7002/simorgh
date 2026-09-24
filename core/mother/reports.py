from __future__ import annotations
from .local_model import prepare_local_model_environment

import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from core.llm_local import generate
from core.identity import SIMORGH_IDENTITY

from .ledger import MotherLedger, utc_now


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReportEngine:
    def __init__(self, ledger: MotherLedger):
        self.ledger = ledger

    @staticmethod
    def _human_period(now: datetime) -> tuple[str, str]:
        local = now.astimezone()
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.astimezone(timezone.utc).isoformat(), now.isoformat()

    def _base_report(self, report_type: str, start: str, end: str) -> dict[str, Any]:
        events = self.ledger.events_between(start, end, limit=10000)
        snapshots = self.ledger.snapshots_since(start)
        counters = Counter((e["event_type"], e["severity"]) for e in events)
        components = Counter(e["component"] for e in events)
        return {
            "report_type": report_type,
            "period": {"start": start, "end": end},
            "generated_at": utc_now(),
            "events_total": len(events),
            "events_by_type": {f"{k[0]}:{k[1]}": v for k, v in counters.items()},
            "events_by_component": dict(components),
            "snapshots_count": len(snapshots),
            "snapshots": snapshots[-50:],
            "latest_state": snapshots[-1] if snapshots else self.ledger.latest_snapshot(),
            "goals": self.ledger.list_goals(),
            "known_unknowns": [],
            "activity": events,
        }

    def _change_summary(self, snapshots: list[dict[str, Any]]) -> list[str]:
        if len(snapshots) < 2:
            return ["برای مقایسهٔ امروز با وضعیت قبلی snapshot کافی ثبت نشده است."]
        first, last = snapshots[0], snapshots[-1]
        changes = []
        for section in ("cpu", "memory", "swap", "disk"):
            a, b = first.get(section, {}), last.get(section, {})
            for key in ("percent", "used_mb", "available_mb", "free_gb"):
                if key in a and key in b and a[key] != b[key]:
                    changes.append(f"{section}.{key}: {a[key]} → {b[key]}")
        return changes[:40] or ["تغییر عددی مهمی در معیارهای اصلی مشاهده نشد."]

    def _local_model_reflection(self, report: dict[str, Any]) -> dict[str, Any]:
        """Optional local-model analysis. It never applies changes."""
        compact = {
            "events": report["events_total"],
            "event_types": report["events_by_type"],
            "components": report["events_by_component"],
            "goals": report["goals"],
            "changes": self._change_summary(report.get("snapshots", []))
            if isinstance(report.get("snapshots"), list)
            else [],
        }
        prompt = (
            "گزارش زیر وضعیت واقعی سیستم است. فقط سه بخش JSON بده: "
            "self_knowledge, weaknesses, candidate_improvements. "
            "هیچ واقعیتی را که در ورودی نیست نساز. برای هر مورد evidence بنویس. "
            "candidate_improvements فقط پیشنهاد باشند، نه دستور اجرا.\n\n"
            + json.dumps(compact, ensure_ascii=False, default=str)
        )
        try:
            prepare_local_model_environment()
            text = generate(
                SIMORGH_IDENTITY,
                prompt,
                max_tokens=500,
                needs_quality=True,
            )
            if not text:
                return {"status": "NOT_AVAILABLE", "reason": "local_model_unavailable"}
            return {
                "status": "ADVISORY",
                "raw": text,
                "ai_generated": True,
            }
        except Exception as exc:
            return {"status": "NOT_AVAILABLE", "reason": type(exc).__name__}

    def daily(self, now: datetime | None = None, *, with_ai: bool = True) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        start, end = self._human_period(now)
        report = self._base_report("DAILY", start, end)
        report["changes"] = self._change_summary(report["snapshots"])
        report["vs_previous_day"] = self._compare_previous_day(_dt(start), report["latest_state"])
        quality = self.ledger.latest_event("daily_test_run")
        report["latest_quality_check"] = quality
        report["self_reflection"] = (
            self._local_model_reflection(report)
            if with_ai
            else (self.ledger.latest_report("DAILY").get("self_reflection")
                  or {"status": "NOT_AVAILABLE", "reason": "daily_ai_refresh_skipped"})
        )
        if not report["activity"]:
            report["known_unknowns"].append(
                "هیچ رویداد قابل مشاهده‌ای برای این بازه ثبت نشده است."
            )
        report["offline_boundary"] = (
            "در بازهٔ خاموشی کامل، مشاهدهٔ زنده ممکن نیست؛ گزارش فقط آخرین وضعیت ثبت‌شده "
            "و رویدادهای قبل و بعد از خاموشی را گزارش می‌کند."
        )
        self.ledger.save_report("DAILY", start, end, report)
        return report

    def _compare_previous_day(self, current_start: datetime, latest: dict[str, Any]) -> dict[str, Any]:
        previous_start = current_start - timedelta(days=1)
        candidates = [
            s for s in self.ledger.snapshots_since(previous_start.isoformat())
            if previous_start <= _dt(s.get("timestamp", "1970-01-01T00:00:00+00:00")) < current_start
        ]
        if not candidates:
            return {"status": "NOT_AVAILABLE", "reason": "no_previous_day_snapshot"}
        previous = max(candidates, key=lambda s: s.get("timestamp", ""))
        return {
            "status": "COMPARABLE",
            "metrics": {
                "cpu_percent": {"previous": previous.get("cpu", {}).get("percent"), "current": latest.get("cpu", {}).get("percent") if latest else None},
                "ram_percent": {"previous": previous.get("memory", {}).get("percent"), "current": latest.get("memory", {}).get("percent") if latest else None},
                "swap_percent": {"previous": previous.get("swap", {}).get("percent"), "current": latest.get("swap", {}).get("percent") if latest else None},
                "disk_percent": {"previous": previous.get("disk", {}).get("percent"), "current": latest.get("disk", {}).get("percent") if latest else None},
            },
            "note": "این مقایسهٔ عددی است و به‌تنهایی به معنی بهتر یا بدتر بودن کلی نیست.",
        }

    def post_boot(self, boot: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        report = self._base_report("POST_BOOT", boot.get("started_at", now.isoformat()), now.isoformat())
        previous = boot.get("previous_boot_id")
        previous_state = None
        for snap in self.ledger.snapshots_since("1970-01-01T00:00:00+00:00"):
            if snap.get("boot_id") == previous:
                previous_state = snap
        previous_events = self.ledger.events_for_boot(previous, limit=2000) if previous else []
        report["boot"] = boot
        report["previous_boot_last_state"] = previous_state
        report["previous_boot_activity"] = previous_events
        report["previous_boot_activity_count"] = len(previous_events)
        if boot.get("previous_shutdown_at") and boot.get("started_at"):
            try:
                offline_seconds = (_dt(boot["started_at"]) - _dt(boot["previous_shutdown_at"])).total_seconds()
                report["offline_interval_seconds"] = max(0, round(offline_seconds, 3))
            except (TypeError, ValueError):
                report["offline_interval_seconds"] = None
        if boot.get("previous_clean_shutdown") is not True:
            report["known_unknowns"].append(
                "خاموشی قبلی clean ثبت نشده است؛ قطع برق/کرش/ریست سخت محتمل است، اما علت دقیق VERIFIED نیست."
            )
        report["offline_boundary"] = (
            "برای بازهٔ خاموشی، Mother فعالیت مشاهده‌شده‌ای ثبت نمی‌کند و چیزی را حدس نمی‌زند."
        )
        self.ledger.save_report("POST_BOOT", boot.get("started_at", now.isoformat()), now.isoformat(), report)
        return report

    def weekly(self, now: datetime | None = None, *, with_ai: bool = True) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).isoformat()
        report = self._base_report("WEEKLY", start, now.isoformat())
        report["changes"] = self._change_summary(self.ledger.snapshots_since(start))
        report["trends"] = self._trends(report["activity"])
        report["service_needs"] = self._service_needs(report)
        report["next_candidate_objectives"] = self._candidate_objectives(report)
        report["capability_matrix"] = self._capability_matrix()
        report["self_reflection"] = (
            self._local_model_reflection(report)
            if with_ai
            else (self.ledger.latest_report("WEEKLY").get("self_reflection")
                  or {"status": "NOT_AVAILABLE", "reason": "weekly_ai_refresh_skipped"})
        )
        self.ledger.save_report("WEEKLY", start, now.isoformat(), report)
        return report

    def _capability_matrix(self) -> dict[str, Any]:
        root = Path(__file__).resolve().parents[2]
        checks = {
            "system_observation": (root / "core/mother/observer.py").is_file(),
            "persistent_event_ledger": (root / "core/mother/ledger.py").is_file(),
            "daily_weekly_postboot_reports": (root / "core/mother/reports.py").is_file(),
            "local_model_coding_assistance": (root / "core/mother/coding.py").is_file(),
            "web_quarantine_gateway": (root / "core/mother/research.py").is_file(),
            "quality_feedback_loop": (root / "core/mother/quality.py").is_file(),
            "godot_state_bridge": (root / "godot/mother_bridge.gd").is_file(),
            "reviewer_gate": (root / "core/orchestration/reviewer.py").is_file(),
            "provenance_memory": (root / "core/memory.py").is_file(),
            "offline_core": (root / "main.py").is_file(),
        }
        implemented = [name for name, ok in checks.items() if ok]
        missing = [name for name, ok in checks.items() if not ok]
        return {
            "status": "MEASURED",
            "implemented_count": len(implemented),
            "total_count": len(checks),
            "implemented": implemented,
            "missing": missing,
            "note": "وجود فایل به‌تنهایی کیفیت قابلیت را ثابت نمی‌کند؛ آزمون و شواهد runtime نیز باید بررسی شوند.",
        }

    @staticmethod
    def _trends(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts = Counter(e["component"] for e in events)
        by_type = Counter(e["event_type"] for e in events)
        return [
            {"type": "component_activity", "values": counts.most_common(10)},
            {"type": "event_activity", "values": by_type.most_common(15)},
        ]

    @staticmethod
    def _service_needs(report: dict[str, Any]) -> list[str]:
        needs = []
        for key, count in report["events_by_type"].items():
            if any(token in key for token in ("failed:", "error:", "restart")) and count > 2:
                needs.append(f"تکرار قابل توجه رویداد {key} با تعداد {count}")
        if not needs:
            needs.append("نیاز بحرانی خودکار از دادهٔ این هفته استخراج نشد.")
        return needs

    @staticmethod
    def _candidate_objectives(report: dict[str, Any]) -> list[str]:
        objectives = []
        if report["events_total"] > 0:
            objectives.append("کامل‌تر کردن پوشش مشاهدهٔ systemd/journal و کاهش NOT_AVAILABLE ها")
        objectives.append("حفظ جداسازی KNOW/INFERRED/UNKNOWN در تمام گزارش‌ها")
        objectives.append("آزمون روزانهٔ مسیرهای مهم و ثبت regression قبل از هر اصلاح")
        return objectives

    def ensure_scheduled_reports(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        latest_daily = self.ledger.latest_report("DAILY")
        latest_weekly = self.ledger.latest_report("WEEKLY")
        latest_post = self.ledger.latest_report("POST_BOOT")
        result: dict[str, Any] = {}
        if not latest_post or latest_post.get("boot", {}).get("boot_id") != self.ledger.boot_id():
            boot = self.ledger.begin_boot()
            result["post_boot"] = self.post_boot(boot, now)
        if not latest_daily or _dt(latest_daily["_ledger"]["created_at"]).date() != now.date():
            result["daily"] = self.daily(now)
        if now.weekday() == 6 and (
            not latest_weekly or (_dt(latest_weekly["_ledger"]["created_at"]).date() != now.date())
        ):
            result["weekly"] = self.weekly(now)
        return result
