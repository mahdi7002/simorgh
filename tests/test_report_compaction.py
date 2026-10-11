import copy, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.mother.ledger import compact_report_payload


def test_small_payload_unchanged():
    p = {"a": [1, 2, 3], "b": {"c": "x"}}
    assert compact_report_payload(p) == p


def test_long_string_truncated():
    out = compact_report_payload({"s": "x" * 10000})
    assert len(out["s"]) < 2300 and "COMPACTED_STR" in out["s"]


def test_long_list_truncated_with_sibling_marker():
    out = compact_report_payload({"activity": [{"i": i} for i in range(500)]})
    assert len(out["activity"]) == 100
    assert out["activity__compacted_omitted"] == 400


def test_input_not_mutated():
    p = {"activity": [{"d": "y" * 5000} for _ in range(300)]}
    before = copy.deepcopy(p)
    compact_report_payload(p)
    assert p == before


def test_two_pass_bounds_a_huge_report():
    events = [{"event_type": "journal_activity", "data": {"lines": ["y" * 500 for _ in range(300)]}} for _ in range(5000)]
    first = compact_report_payload({"activity": events})
    second = compact_report_payload(first, str_max=400, list_max=20)
    assert len(json.dumps(second)) < 1_000_000
