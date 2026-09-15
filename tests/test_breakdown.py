from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core.breakdown import build_breakdown

ROOT = Path(__file__).resolve().parents[1]


def test_breakdown_is_safe_without_catalog():
    assert not (ROOT / "catalog.json").exists()
    assert not build_breakdown()


def test_breakdown_loads_explicit_catalog(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        '{"standalone_docs_unique": ['
        '"/home/example/docs/a.txt",'
        '"/home/example/docs/b.txt",'
        '"relative/c.txt"]}',
        encoding="utf-8",
    )
    result = build_breakdown(catalog)
    assert result["docs"] == 2
    assert result["relative"] == 1


def test_breakdown_import_has_no_output_or_failure():
    result = subprocess.run(
        [sys.executable, "-c", "import core.breakdown"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
