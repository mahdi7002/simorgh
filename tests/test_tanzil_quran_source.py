from pathlib import Path
import subprocess
import sys

import pytest


def test_tanzil_ansarian_exact_match_when_network_available():
    """Network-backed provenance check; offline developer runs skip cleanly."""
    script = Path("scripts/verify_tanzil_quran_db.py")
    db = Path("data/grid/quran.db")
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--db", str(db)],
            capture_output=True,
            text=True,
            timeout=40,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        pytest.skip(f"Tanzil network verification unavailable: {exc}")

    if result.returncode != 0 and any(
        token in (result.stdout + result.stderr).lower()
        for token in ("urlopen", "temporary failure in name resolution", "network is unreachable")
    ):
        pytest.skip("Tanzil network verification unavailable")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "TANZIL_EXACT_MATCH: PASS" in result.stdout
