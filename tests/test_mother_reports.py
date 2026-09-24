from __future__ import annotations

from datetime import datetime, timezone

from core.mother.ledger import MotherLedger
from core.mother.reports import ReportEngine


def test_daily_report_has_previous_day_comparison_when_snapshot_exists(tmp_path):
    ledger = MotherLedger(tmp_path / "mother.db")
    ledger.save_snapshot({
        "timestamp": "2026-09-23T12:00:00+00:00",
        "boot_id": "old",
        "cpu": {"percent": 10},
        "memory": {"percent": 20},
        "swap": {"percent": 0},
        "disk": {"percent": 40},
    })
    ledger.save_snapshot({
        "timestamp": "2026-09-24T12:00:00+00:00",
        "boot_id": "new",
        "cpu": {"percent": 15},
        "memory": {"percent": 25},
        "swap": {"percent": 1},
        "disk": {"percent": 41},
    })
    report = ReportEngine(ledger).daily(datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc))
    assert report["vs_previous_day"]["status"] == "COMPARABLE"
    assert report["vs_previous_day"]["metrics"]["cpu_percent"]["previous"] == 10
