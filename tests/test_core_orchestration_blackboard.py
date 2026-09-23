"""Tests for core/orchestration/blackboard.py (mission M-c18b8f)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.orchestration.blackboard import Blackboard


def test_init_defaults_are_empty():
    b = Blackboard(query="سؤال")
    assert b.selected_agents == []
    assert b.outputs == {}
    assert b.ai_generated == {}
    assert b.tool_results == {}
    assert b.review == {}


def test_record_output_stores_text_and_ai_flag():
    b = Blackboard(query="q")
    b.record_output("hakim", "پاسخ حکیم", ai_generated=True)
    assert b.outputs["hakim"] == "پاسخ حکیم"
    assert b.ai_generated["hakim"] is True


def test_record_output_defaults_ai_generated_to_false():
    b = Blackboard(query="q")
    b.record_output("hafez", "یک غزل")
    assert b.ai_generated["hafez"] is False


def test_record_output_overwrites_same_agent():
    b = Blackboard(query="q")
    b.record_output("hakim", "اول")
    b.record_output("hakim", "دوم")
    assert b.outputs["hakim"] == "دوم"


def test_record_tool_result_stores_by_name():
    b = Blackboard(query="q")
    b.record_tool_result("quran_search", {"status": "OK", "data": ["آیه"]})
    assert b.tool_results["quran_search"]["status"] == "OK"


def test_as_dict_reflects_all_fields():
    b = Blackboard(query="q")
    b.selected_agents.append("hakim")
    b.record_output("hakim", "پاسخ")
    b.record_tool_result("t", {"ok": True})
    b.review["approved"] = True
    d = b.as_dict()
    assert d["query"] == "q"
    assert d["selected_agents"] == ["hakim"]
    assert d["outputs"] == {"hakim": "پاسخ"}
    assert d["tool_results"] == {"t": {"ok": True}}
    assert d["review"] == {"approved": True}


def test_as_dict_returns_independent_copies():
    b = Blackboard(query="q")
    b.record_output("hakim", "پاسخ")
    d = b.as_dict()
    d["outputs"]["hakim"] = "دستکاری‌شده"
    assert b.outputs["hakim"] == "پاسخ"
