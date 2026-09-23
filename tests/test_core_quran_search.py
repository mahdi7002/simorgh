"""Tests for core/quran_search.py (mission M-9d7de6).

Builds a small FTS5 table matching knowledge_fts's real schema
(source, category, content) and points SIMORGH_QURAN_DB at it via
reload, so the real quran.db is never touched.
"""
import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROWS = [
    ("قرآن", "معنوی", "سوره 2 آیه 45 | از صبر و نماز کمک بخواهید."),
    ("قرآن", "معنوی", "سوره 94 آیه 5 | همانا با سختی آسانی است."),
    ("تفسیر المیزان", "تفسیر", "شرح صبر در آیات قرآن، بدون قالب سوره/آیه."),
]


@pytest.fixture
def qs(tmp_path, monkeypatch):
    db_path = tmp_path / "quran.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE VIRTUAL TABLE knowledge_fts USING fts5(source, category, content)")
    conn.executemany("INSERT INTO knowledge_fts (source, category, content) VALUES (?, ?, ?)", ROWS)
    conn.commit()
    conn.close()

    monkeypatch.setenv("SIMORGH_QURAN_DB", str(db_path))
    import core.quran_search as qs_mod
    importlib.reload(qs_mod)
    yield qs_mod

    monkeypatch.undo()
    importlib.reload(qs_mod)


def test_extract_keywords_drops_stopwords_and_short_words(qs):
    kws = qs._extract_keywords("من چیکار کنم که صبر داشته باشم")
    assert "صبر" in kws
    assert "من" not in kws
    assert "کنم" not in kws


def test_extract_keywords_respects_max_words(qs):
    kws = qs._extract_keywords("صبر شکیبایی آسانی سختی نماز دعا مناجات", max_words=3)
    assert len(kws) == 3


def test_get_quran_wisdom_finds_matching_ayah(qs):
    results = qs.get_quran_wisdom("صبر در سختی")
    assert len(results) >= 1
    assert any(r["surah"] == "2" and r["ayah"] == "45" for r in results)


def test_get_quran_wisdom_only_returns_spiritual_category(qs):
    results = qs.get_quran_wisdom("شرح صبر آیات")
    texts = [r["text"] for r in results]
    assert not any("بدون قالب" in t for t in texts)


def test_get_quran_wisdom_respects_limit(qs):
    results = qs.get_quran_wisdom("صبر", limit=1)
    assert len(results) <= 1


def test_get_quran_wisdom_no_keywords_returns_empty(qs):
    assert qs.get_quran_wisdom("این را به من بگو") == []


def test_get_quran_wisdom_missing_db_returns_empty(qs, monkeypatch, tmp_path):
    monkeypatch.setenv("SIMORGH_QURAN_DB", str(tmp_path / "does_not_exist.db"))
    importlib.reload(qs)
    assert qs.get_quran_wisdom("صبر") == []


def test_format_for_prompt_empty_list(qs):
    assert qs.format_for_prompt([]) == ""


def test_format_for_prompt_includes_surah_and_ayah(qs):
    text = qs.format_for_prompt([{"surah": "2", "ayah": "45", "text": "نمونه"}])
    assert "سوره 2" in text
    assert "آیه 45" in text
    assert "نمونه" in text


def test_format_for_prompt_handles_missing_surah(qs):
    text = qs.format_for_prompt([{"surah": "", "ayah": "", "text": "نمونه بدون منبع"}])
    assert "نمونه بدون منبع" in text
    assert "سوره" not in text
