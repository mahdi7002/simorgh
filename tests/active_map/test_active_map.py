import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "scripts" / "simorgh_active_map.py"


def test_scanner_compiles():
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SCANNER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_schema_exists():
    schema = ROOT / "schemas" / "simorgh_active_map_v1.json"
    assert schema.exists()
    data = json.loads(schema.read_text(encoding="utf-8"))
    assert data["title"] == "SIMORGH Active Map V1"


def test_scanner_help():
    result = subprocess.run(
        [sys.executable, str(SCANNER), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
