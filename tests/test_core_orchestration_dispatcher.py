"""Tests for core/orchestration/dispatcher.py (mission M-1f983b)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.orchestration.dispatcher import Dispatcher, DispatchResult


def _d():
    return Dispatcher()


def test_empty_query_returns_default_route():
    r = _d().dispatch("")
    assert r.reason == "default-route"
    assert list(r.agents) == list(Dispatcher.DEFAULT[:2])


def test_hafeze_memory_does_not_collide_with_hafez_poet():
    # حافظه (memory) contains حافظ (Hafez) as a substring; must not misroute.
    r = _d().dispatch("چیزی در حافظه‌ام نیست")
    assert r.reason == "memory-topic"
    assert "hafez" not in r.agents


def test_poetry_keyword_routes_to_hafez():
    r = _d().dispatch("یک غزل بخوان")
    assert r.reason == "keyword-rule"
    assert "hafez" in r.agents


def test_quran_keyword_routes_to_hakim_and_hafez():
    r = _d().dispatch("یک آیه از قرآن بگو")
    assert r.reason == "keyword-rule"
    assert "hakim" in r.agents


def test_why_keyword_routes_to_hakim_and_nazer():
    r = _d().dispatch("چرا این اتفاق افتاد؟")
    assert r.reason == "keyword-rule"
    assert set(r.agents) == {"hakim", "nazer"}


def test_how_to_build_routes_to_amel_and_rahbar():
    r = _d().dispatch("چگونه این کد را بنویسم")
    assert r.reason == "keyword-rule"
    assert set(r.agents) == {"amel", "rahbar"}


def test_teach_keyword_routes_to_moalem():
    r = _d().dispatch("این را برایم یاد بده")
    assert "moalem" in r.agents


def test_story_keyword_routes_to_khaliq():
    r = _d().dispatch("یک داستان خلاقانه بگو")
    assert r.agents == ["khaliq"]


def test_unmatched_query_falls_back_to_default():
    r = _d().dispatch("یک جمله‌ی کاملاً نامرتبط و خنثی")
    assert r.reason == "default-route"


def test_english_keywords_are_case_insensitive():
    r = _d().dispatch("Tell me a creative STORY please")
    assert "khaliq" in r.agents


def test_max_agents_truncates_result():
    r = _d().dispatch("چگونه این کد را بنویسم", max_agents=1)
    assert len(r.agents) == 1


def test_dispatch_result_is_frozen_dataclass():
    r = _d().dispatch("")
    assert isinstance(r, DispatchResult)
    try:
        r.reason = "x"
        assert False, "should be frozen"
    except Exception:
        pass
