import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_gate(*args):
    return subprocess.run(
        [sys.executable, "scripts/compliance_gate.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_compliance_audit_runs_and_reports_rights_gap():
    result = run_gate()
    assert result.returncode == 0, result.stderr
    assert "asset_rights_verified" in result.stdout


def test_strict_release_gate_fails_closed_without_human_signoff():
    result = run_gate("--release")
    assert result.returncode != 0
    assert "human_release_signoff" in result.stdout
