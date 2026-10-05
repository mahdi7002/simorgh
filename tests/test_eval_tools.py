import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "eval" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_wilson_matches_known_values():
    run_eval = _load("run_eval")
    assert run_eval.wilson(287, 287)[1] == 100.0 and 98.0 < run_eval.wilson(287, 287)[0] < 99.0
    lo, hi = run_eval.wilson(106, 300)
    assert 30.0 < lo < 31.0 and 40.0 < hi < 41.5
    assert run_eval.wilson(0, 0) == (0.0, 0.0)


def test_importer_maps_flexible_keys_and_refuses_unknown(tmp_path):
    imp = _load("import_fa_eval")
    src = tmp_path / "b.jsonl"
    src.write_text("\n".join([
        json.dumps({"question": "پایتخت ایران؟", "answer": "تهران"}, ensure_ascii=False),
        json.dumps({"q": "x", "gold": ["الف", "ب"], "task": "classification"}, ensure_ascii=False),
        json.dumps({"q": "ناشناخته؟", "answer": "n/a", "type": "abstain"}, ensure_ascii=False),
        json.dumps({"weird": 1}),
    ]), encoding="utf-8")
    items, skipped = imp.convert(imp.load_records(src))
    assert [i["type"] for i in items] == ["qa", "classify", "abstain"] and skipped == [4]
    assert items[1]["expected_any"] == ["الف", "ب"] and "نمی‌دانم" in items[2]["expected_any"]
    bad = tmp_path / "c.jsonl"
    bad.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    assert imp.convert(imp.load_records(bad))[0] == []


def test_finalize_evidence_writes_report_from_real_counts(tmp_path, monkeypatch):
    from app.knowledge import poetry_lookup as pl

    db = tmp_path / "v.db"
    conn = sqlite3.connect(db)
    conn.execute("create table poets(id integer primary key, name text)")
    conn.execute("create table verses(id integer primary key, poet_id int, poem_id int, bait_number int, text text)")
    conn.execute("create virtual table verses_fts using fts5(text)")
    vocab = "عشق دل جان باغ گل شب روز ماه خورشید دریا کوه راه دوست یار نور سایه باد خاک آب آتش چشم سخن راز پرده نی می ساقی بهار زمستان شمشیر کمان اسب سوار شهر دشت رود پل دروازه دیوار بام کوچه خانه چراغ".split()
    import random
    rng = random.Random(3)
    for pid in range(1, 4):
        conn.execute("insert into poets values (?,?)", (pid, f"شاعر{pid}"))
    for vid in range(1, 301):
        text = " ".join(rng.sample(vocab, 8)) + f" {vid}x{vid}"
        conn.execute("insert into verses values (?,?,?,?,?)", (vid, rng.randint(1, 3), vid, 1, text))
        conn.execute("insert into verses_fts(rowid, text) values (?,?)", (vid, text))
    conn.commit()
    conn.close()
    pl.close()
    monkeypatch.setattr(pl, "DB", str(db))
    fin = _load("finalize_evidence")
    out = tmp_path / "report.md"
    monkeypatch.setattr("sys.argv", ["x", "--n", "30", "--heldout-seeds", "11", "23", "--out", str(out)])
    assert fin.main() == 0
    text = out.read_text(encoding="utf-8")
    assert "Held-out" in text and "two adjacent letters swapped" in text
    assert "pooled n=60" in text
    assert "## Error analysis" in text
    pl.close()
