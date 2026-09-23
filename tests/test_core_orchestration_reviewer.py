"""Tests for core/orchestration/reviewer.py (mission M-4d620a)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.orchestration.reviewer import Reviewer, ReviewResult


def _r():
    return Reviewer()


def test_non_evidence_query_with_output_is_approved():
    res = _r().review("سلام خوبی؟", {"hakim": "سلام، خوبم"}, {})
    assert isinstance(res, ReviewResult)
    assert res.approved is True
    assert res.warnings == []


def test_empty_output_warns():
    res = _r().review("سلام", {"hakim": ""}, {})
    assert "empty_response" in res.warnings
    assert res.approved is False


def test_evidence_sensitive_query_without_tool_evidence_warns():
    res = _r().review("این آیه از قرآن چیست", {"hakim": "پاسخی بدون منبع"}, {})
    assert "evidence_sensitive_request_without_tool_evidence" in res.warnings


def test_hafez_without_hafeze_is_evidence_sensitive():
    res = _r().review("یک غزل از حافظ بخوان", {"hafez": "پاسخ"}, {})
    assert "evidence_sensitive_request_without_tool_evidence" in res.warnings


def test_hafeze_memory_is_not_evidence_sensitive():
    # "حافظه" contains "حافظ" as a substring but must not trigger the gate.
    res = _r().review("چیزی در حافظه‌ام نیست", {"hakim": "پاسخ بدون منبع"}, {})
    assert "evidence_sensitive_request_without_tool_evidence" not in res.warnings


def test_evidence_sensitive_with_matching_tool_evidence_is_approved():
    tool_results = {"quran_search": {"status": "OK", "data": "این متن دقیق آیه است و کافی بلند"}}
    output = "این متن دقیق آیه است و کافی بلند در پاسخ آمده"
    res = _r().review("این آیه از قرآن چیست", {"hakim": output}, tool_results)
    assert "evidence_sensitive_request_without_tool_evidence" not in res.warnings
    assert "quoted_text_does_not_match_retrieved_evidence" not in res.warnings
    assert res.approved is True


def test_evidence_sensitive_with_evidence_but_unquoted_output_warns():
    tool_results = {"quran_search": {"status": "OK", "data": "این یک متن کاملاً متفاوت و طولانی از منبع است"}}
    res = _r().review("این آیه از قرآن چیست", {"hakim": "پاسخی کاملاً بی‌ربط به متن منبع"}, tool_results)
    assert "quoted_text_does_not_match_retrieved_evidence" in res.warnings


def test_failed_tool_result_does_not_count_as_evidence():
    tool_results = {"quran_search": {"status": "ERROR", "data": "چیزی"}}
    res = _r().review("این آیه از قرآن چیست", {"hakim": "پاسخ"}, tool_results)
    assert "evidence_sensitive_request_without_tool_evidence" in res.warnings


def test_empty_data_does_not_count_as_evidence():
    tool_results = {"quran_search": {"status": "OK", "data": ""}}
    res = _r().review("این آیه از قرآن چیست", {"hakim": "پاسخ"}, tool_results)
    assert "evidence_sensitive_request_without_tool_evidence" in res.warnings


def test_generated_claim_without_evidence_warns():
    res = _r().review("سلام", {"hakim": "طبق منابع، این درست است"}, {})
    assert "generated_evidence_claim_without_evidence" in res.warnings


def test_checks_list_is_always_present():
    res = _r().review("q", {"a": "b"}, {})
    assert set(res.checks) == {
        "non_empty_output", "evidence_gate",
        "no_false_evidence_claim", "quoted_text_matches_evidence",
    }


def test_non_dict_tool_results_is_handled_safely():
    res = _r().review("این آیه از قرآن چیست", {"hakim": "پاسخ"}, None)
    assert "evidence_sensitive_request_without_tool_evidence" in res.warnings
