from datetime import datetime
from zoneinfo import ZoneInfo

from core.mother.service import _weekly_report_due


TEHRAN = ZoneInfo("Asia/Tehran")


def test_sunday_0010_needs_report_if_latest_is_previous_local_week():
    now = datetime(2026, 10, 18, 0, 10, tzinfo=TEHRAN)
    previous_week = {
        "_ledger": {"created_at": "2026-10-10T20:40:00+00:00"}
    }

    assert _weekly_report_due(now, previous_week) is True


def test_report_created_sunday_0010_is_not_due_again_five_minutes_later():
    # 20:40 UTC on Saturday is 00:10 Sunday in Tehran.
    just_created = {
        "_ledger": {"created_at": "2026-10-17T20:40:00+00:00"}
    }
    five_minutes_later = datetime(2026, 10, 18, 0, 15, tzinfo=TEHRAN)

    assert _weekly_report_due(five_minutes_later, just_created) is False


def test_weekly_is_not_due_outside_local_sunday():
    now = datetime(2026, 10, 19, 0, 10, tzinfo=TEHRAN)
    assert _weekly_report_due(now, None) is False
