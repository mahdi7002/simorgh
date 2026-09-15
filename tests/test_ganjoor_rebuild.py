from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_ganjoor_rebuild.py"
SPEC = importlib.util.spec_from_file_location("prepare_ganjoor_rebuild", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_load_quarantine_json_list(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "poet": "خیام",
                    "title": "مجموعه اشعار",
                    "text": "نمونه",
                    "source": "github_corpus",
                    "reason": "concatenated-multi-poem (len > 3000)",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows = MODULE.load_quarantine_json(path)
    assert len(rows) == 1
    assert rows[0]["poet"] == "خیام"
    assert rows[0]["reason"].startswith("concatenated-multi-poem")


def test_load_quarantine_json_wrapped_rows(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.json"
    path.write_text(json.dumps({"rows": [{"poet": "حافظ", "title": "غزل"}]}), encoding="utf-8")
    rows = MODULE.load_quarantine_json(path)
    assert rows == [{"poet": "حافظ", "title": "غزل"}]


def test_normalization_handles_persian_variants() -> None:
    assert MODULE.norm("  يِ  ك\u200c  ") == "ی ک"


def test_poem_text_prefers_ordered_verses() -> None:
    poem = {
        "Verses": [
            {"VOrder": 2, "Text": "بیت دوم"},
            {"VOrder": 1, "Text": "بیت اول"},
        ],
        "Sections": [{"PlainText": "fallback"}],
    }
    assert MODULE.poem_text(poem) == "بیت اول\nبیت دوم"


def test_generic_title_detection() -> None:
    assert MODULE.generic_title("مجموعه اشعار")
    assert MODULE.generic_title("اشعار")
    assert not MODULE.generic_title("غزل حافظ")
