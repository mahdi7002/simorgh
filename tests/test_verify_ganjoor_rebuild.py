from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_ganjoor_rebuild.py"
SPEC = importlib.util.spec_from_file_location("verify_ganjoor_rebuild", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_poem_text_preserves_empty_verse_records() -> None:
    poem = {
        "Verses": [
            {"VOrder": 1, "Text": "بیت اول"},
            {"VOrder": 2, "Text": ""},
            {"VOrder": 3, "Text": ""},
        ]
    }
    assert MODULE.poem_text(poem) == "بیت اول\n\n"


def test_poem_text_preserves_verse_order() -> None:
    poem = {
        "Verses": [
            {"VOrder": 2, "Text": "بیت دوم"},
            {"VOrder": 1, "Text": "بیت اول"},
        ],
        "Sections": [{"PlainText": "fallback"}],
    }
    assert MODULE.poem_text(poem) == "بیت اول\nبیت دوم"
