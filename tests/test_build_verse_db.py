import importlib.util
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_verse_db", ROOT / "scripts" / "build_verse_db.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(root, slug, rel, obj):
    p = root / "poets" / slug / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _verses(*pairs):
    out, order = [], 0
    for ci, (a, b) in enumerate(pairs):
        order += 1
        out.append({"VOrder": order, "Position": "Right", "Text": a, "CoupletIndex": ci})
        order += 1
        out.append({"VOrder": order, "Position": "Left", "Text": b, "CoupletIndex": ci})
    return out


FIRST = "بهار آمد و گل شکفت از چمن"


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "ganjoor"
    root.mkdir()
    manifest = {
        "Poets": [
            {"Id": 1, "Nickname": "شاعر آزمون", "FullUrl": "/testa"},
            {"Id": 2, "Nickname": "شاعر دوم", "FullUrl": "/testb"},
        ],
        "PoemsCount": 3,
        "PoetsCount": 2,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    v1 = _verses(
        (FIRST, "نسیم سحر بوی جانان آورد"),
        ("ز هر شاخ مرغی نوایی گرفت", "دل ما به یاد تو جایی گرفت"),
    )
    v1.append(
        {"VOrder": 9, "Position": "Comment", "Text": "توضیح ویراستار", "CoupletIndex": 9}
    )
    _write(
        root,
        "testa",
        "ghazal/sh1.json",
        {
            "FullTitle": "شاعر آزمون » غزلیات » غزل شمارهٔ ۱",
            "Title": "غزل شمارهٔ ۱",
            "Verses": v1,
        },
    )
    _write(
        root,
        "testa",
        "qasida/q1.json",
        {
            "FullTitle": "شاعر آزمون » قصیده بدون دسته",
            "Title": "قصیده",
            "Verses": _verses(
                ("زرّین خـــــویش مي‌روم هر شب", "تا کوی دوست در پی آن مه جبین")
            ),
        },
    )
    _write(root, "testa", "poet.json", {"ignored": True})
    _write(
        root,
        "testb",
        "ghazal/sh1.json",
        {
            "FullTitle": "شاعر دوم » دیوان » غزل ۱",
            "Title": "غزل ۱",
            "Verses": _verses(
                ("ساقیا باده ده که وقت بهار است", "نو گل و باغ و سرو و لاله به کار است")
            ),
        },
    )
    return root


@pytest.fixture(autouse=True)
def _close_poetry_lookup():
    """Force-close the module-level SQLite connection after every test."""
    yield
    try:
        from app.knowledge import poetry_lookup as pl
        if hasattr(pl, "close"):
            pl.close()
    except Exception:
        pass


def test_structure_counts_and_positions(source, tmp_path):
    mod = _builder()
    out = tmp_path / "out" / "verses.db"
    stats = mod.build(source, out, log=lambda *_a: None)
    assert (stats["poets"], stats["poems"], stats["verses"]) == (2, 3, 8)
    assert not out.with_name(out.name + ".part").exists()
    with closing(sqlite3.connect(out)) as c:
        rows = c.execute(
            "SELECT verse_order, bait_number, position_in_bait "
            "FROM verses WHERE poem_id=1 ORDER BY verse_order"
        ).fetchall()
        assert rows == [(1, 1, 1), (2, 1, 2), (3, 2, 1), (4, 2, 2)]
        assert (
            c.execute("SELECT count(*) FROM verses WHERE text LIKE '%ویراستار%'").fetchone()[0]
            == 0
        )


def test_full_text_has_one_line_per_bait(source, tmp_path):
    out = tmp_path / "v.db"
    _builder().build(source, out, log=lambda *_a: None)
    with closing(sqlite3.connect(out)) as c:
        full = c.execute("SELECT full_text FROM poems WHERE id=1").fetchone()[0]
    lines = full.split("\n")
    assert len(lines) == 2 and lines[0] == FIRST + "    " + "نسیم سحر بوی جانان آورد"


def test_books_come_from_the_full_title(source, tmp_path):
    out = tmp_path / "v.db"
    _builder().build(source, out, log=lambda *_a: None)
    with closing(sqlite3.connect(out)) as c:
        titles = {
            r[0]
            for r in c.execute(
                "SELECT b.title FROM books b "
                "JOIN poets p ON p.id=b.poet_id WHERE p.name='شاعر آزمون'"
            )
        }
    assert titles == {"غزلیات", "شاعر آزمون"}



def test_source_provenance_positions_and_paragraph_exclusion(source, tmp_path):
    mod = _builder()
    _write(
        source,
        "testa",
        "structured/sh1.json",
        {
            "FullTitle": "شاعر آزمون » ساختار » نمونه",
            "Title": "نمونه",
            "Verses": [
                {"VOrder": 1, "Position": "Right", "Text": "  آغاز  ", "CoupletIndex": 0},
                {"VOrder": 2, "Position": "Left", "Text": "پایان", "CoupletIndex": 0},
                {"VOrder": 3, "Position": "CenteredVerse1", "Text": "بند نخست", "CoupletIndex": 1},
                {"VOrder": 4, "Position": "CenteredVerse2", "Text": "بند دوم", "CoupletIndex": 1},
                {"VOrder": 5, "Position": "Single", "Text": "سطر آزاد", "CoupletIndex": 2},
                {"VOrder": 6, "Position": "Paragraph", "Text": "این نثر نباید نمایه شود", "CoupletIndex": 3},
                {"VOrder": 7, "Position": "Comment", "Text": "این توضیح نباید نمایه شود", "CoupletIndex": 4},
            ],
        },
    )

    out = tmp_path / "source-fields.db"
    stats = mod.build(source, out, log=lambda *_a: None)
    assert stats["poems"] == 4
    assert stats["verses"] == 13

    source_path = "poets/testa/structured/sh1.json"
    with closing(sqlite3.connect(out)) as c:
        poem = c.execute(
            "SELECT source_path, source_full_title, source_category_title, "
            "full_text, verse_count FROM poems WHERE source_path=?",
            (source_path,),
        ).fetchone()
        rows = c.execute(
            "SELECT v.text, v.position_in_bait, v.source_position, "
            "v.source_vorder, v.source_couplet_index "
            "FROM verses v JOIN poems p ON p.id=v.poem_id "
            "WHERE p.source_path=? ORDER BY v.verse_order",
            (source_path,),
        ).fetchall()

    assert poem is not None
    assert poem[0] == source_path
    assert poem[1] == "شاعر آزمون » ساختار » نمونه"
    assert poem[2] is None
    assert poem[4] == 5
    assert "این نثر نباید نمایه شود" not in poem[3]
    assert "این توضیح نباید نمایه شود" not in poem[3]
    assert rows == [
        ("  آغاز  ", 1, "Right", 1, 0),
        ("پایان", 2, "Left", 2, 0),
        ("بند نخست", 1, "CenteredVerse1", 3, 1),
        ("بند دوم", 2, "CenteredVerse2", 4, 1),
        ("سطر آزاد", 1, "Single", 5, 2),
    ]


def test_unknown_nonempty_source_position_fails_closed():
    mod = _builder()
    with pytest.raises(ValueError, match="unsupported Ganjoor Position"):
        mod.extract(
            {
                "FullTitle": "شاعر » کتاب » شعر",
                "Title": "شعر",
                "Verses": [
                    {
                        "VOrder": 1,
                        "Position": "FuturePosition",
                        "Text": "موقعیت ناشناخته",
                        "CoupletIndex": 0,
                    }
                ],
            },
            "شاعر",
        )


def test_normalizer():
    mod = _builder()
    assert mod.normalize_for_index("زرّین خـــــویش مي‌روم") == "زرین خویش می روم"
    assert mod.normalize_for_index("گیتى كه") == "گیتی که"
    assert mod.normalize_for_index("طرهٔ") == "طرهٔ"


def test_poet_filter_and_build_info(source, tmp_path):
    out = tmp_path / "v.db"
    stats = _builder().build(source, out, poets=["testa"], log=lambda *_a: None)
    assert stats["poets"] == 1
    with closing(sqlite3.connect(out)) as c:
        info = dict(c.execute("SELECT key, value FROM build_info"))
    assert "ganjoor" in info["credit"].lower() and info["source_remote"].endswith(
        "ganjoor-data"
    )


def test_cli_returns_zero(source, tmp_path):
    out = tmp_path / "cli.db"
    assert _builder().main(["--source-dir", str(source), "--output", str(out)]) == 0
    assert out.is_file()


def test_missing_manifest_fails(tmp_path):
    with pytest.raises((SystemExit, FileNotFoundError)):
        _builder().build(tmp_path, tmp_path / "x.db", log=lambda *_a: None)


def test_lookup_works_on_a_built_database(source, tmp_path, monkeypatch):
    from app.knowledge import poetry_lookup as pl

    out = tmp_path / "v.db"
    _builder().build(source, out, log=lambda *_a: None)

    monkeypatch.setattr(pl, "DB", str(out))
    pl.close()  # ensure no leftover connection to the real DB

    try:
        r = pl.lookup(FIRST)
        assert r is not None
        assert r.get("status") == "answer"
        assert r.get("poet") == "شاعر آزمون"
        attr = pl.attribution(FIRST + " از کیست") or ""
        assert "شاعر آزمون" in attr
    finally:
        pl.close()

def test_builder_refuses_existing_output_and_sidecars(source, tmp_path):
    mod = _builder()
    for kind in ("output", "part", "metadata"):
        out = tmp_path / f"{kind}.db"
        protected = {
            "output": out,
            "part": out.with_name(out.name + ".part"),
            "metadata": out.with_name(out.name + ".build.json"),
        }[kind]
        sentinel = f"preserve-{kind}".encode()
        protected.write_bytes(sentinel)

        with pytest.raises(FileExistsError, match="refusing to overwrite"):
            mod.build(source, out, log=lambda *_a: None)

        assert protected.read_bytes() == sentinel
        if kind != "output":
            assert not out.exists()
