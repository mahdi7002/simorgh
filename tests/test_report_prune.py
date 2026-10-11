import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.mother.ledger import select_reports_to_prune

OLD, NEW, CUT = "2026-01-01T00:00:00+00:00", "2026-10-10T00:00:00+00:00", "2026-10-04T00:00:00+00:00"


def test_newest_per_type_always_kept_even_if_old():
    rows = [(1, "DAILY", OLD, 10), (2, "DAILY", OLD, 10), (3, "WEEKLY", OLD, 10)]
    assert select_reports_to_prune(rows, CUT, 10**9) == [1]


def test_recent_rows_kept_old_deleted():
    rows = [(1, "DAILY", OLD, 10), (2, "DAILY", NEW, 10), (3, "DAILY", NEW, 10)]
    assert select_reports_to_prune(rows, CUT, 10**9) == [1]


def test_size_guard_keeps_only_newest_per_type():
    rows = [(1, "DAILY", NEW, 600), (2, "DAILY", NEW, 600), (3, "POST_BOOT", NEW, 600)]
    assert select_reports_to_prune(rows, CUT, 1000) == [1]


def test_empty_and_single():
    assert select_reports_to_prune([], CUT, 1000) == []
    assert select_reports_to_prune([(1, "DAILY", OLD, 5)], CUT, 1000) == []
