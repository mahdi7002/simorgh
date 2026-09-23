"""Tests for core/engine/memory_graph.py (mission M-e4d51f).

DB_PATH is a plain module-level string re-read on every call, so
monkeypatch.setattr on the module is enough to redirect every function
to a tmp_path database — the real data/simorgh.db is never touched.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.engine.memory_graph as mg


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(mg, "DB_PATH", str(tmp_path / "test.db"))
    mg.init_db()
    return mg


def _table_names(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')").fetchall()
    conn.close()
    return {r[0] for r in rows}


def test_init_db_creates_all_expected_tables(db):
    names = _table_names(db.DB_PATH)
    for expected in ("nodes", "edges", "memory_fts", "fast_cache",
                      "personal_memory", "tasks", "short_term_memory", "terminal_history"):
        assert expected in names


def test_add_node_is_searchable_via_fts(db):
    db.add_node("concept", "صبر", {"note": "test"})
    results = db.search_nodes_by_keyword("صبر")
    assert any(r["name"] == "صبر" and r["type"] == "concept" for r in results)


def test_add_node_called_twice_creates_two_rows(db):
    # nodes has no UNIQUE constraint on name, so "INSERT OR IGNORE" never
    # actually triggers here — this documents the real (duplicate-prone)
    # behavior rather than an intended dedup that doesn't exist in the code.
    db.add_node("concept", "تکرار")
    db.add_node("concept", "تکرار")
    conn = sqlite3.connect(db.DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM nodes WHERE name=?", ("تکرار",)).fetchone()[0]
    conn.close()
    assert count == 2


def test_add_edge_creates_concept_nodes_and_relation(db):
    db.add_edge("باران", "رویش", "causes", "علت رویش", confidence=0.9)
    related = db.find_related_nodes("باران", direction="outgoing")
    assert any(r["target"] == "رویش" and r["relation"] == "causes" for r in related)


def test_query_cause_graph_returns_explanation(db):
    db.add_edge("قحطی", "مهاجرت", "causes", "علت مهاجرت")
    text = db.query_cause_graph("مهاجرت")
    assert "قحطی" in text
    assert "علت مهاجرت" in text


def test_find_related_nodes_incoming_direction(db):
    db.add_edge("الف", "ب", "leads_to")
    related = db.find_related_nodes("ب", direction="incoming")
    assert any(r["source"] == "الف" for r in related)


def test_find_related_nodes_respects_max_depth(db):
    db.add_edge("a1", "a2", "leads_to")
    db.add_edge("a2", "a3", "leads_to")
    shallow = db.find_related_nodes("a1", direction="outgoing", max_depth=1)
    deep = db.find_related_nodes("a1", direction="outgoing", max_depth=2)
    assert not any(r["target"] == "a3" for r in shallow)
    assert any(r["target"] == "a3" for r in deep)


def test_save_interaction_creates_event_node(db):
    db.save_interaction("سؤال تستی", "پاسخ تستی")
    conn = sqlite3.connect(db.DB_PATH)
    row = conn.execute("SELECT type, name FROM nodes WHERE type='event'").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "event"
    assert row[1].startswith("سؤال تستی")


def test_cache_response_is_deduped_by_query_hash(db):
    db.cache_response("همان سؤال", "پاسخ اول")
    db.cache_response("همان سؤال", "پاسخ دوم")
    conn = sqlite3.connect(db.DB_PATH)
    rows = conn.execute("SELECT response FROM fast_cache").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "پاسخ دوم"
