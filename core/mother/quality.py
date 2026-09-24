from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .ledger import MotherLedger
from .coding import propose_patch

ROOT = Path(__file__).resolve().parents[2]


def run_daily_quality_check(ledger: MotherLedger) -> dict[str, Any]:
    python = str(ROOT / ".venv" / "bin" / "python")
    if not Path(python).is_file():
        python = "python3"
    command = os.environ.get("SIMORGH_MOTHER_TEST_COMMAND")
    if command:
        args = ["bash", "-lc", command]
    else:
        args = [python, "-m", "pytest", "-q"]

    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    payload = {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-12000:],
    }
    ledger.record_event(
        component="quality",
        event_type="daily_test_run",
        actor="mother",
        action="verify",
        severity="info" if result.returncode == 0 else "error",
        verified=True,
        provenance="local_test_runner",
        data=payload,
    )

    proposal = None
    if result.returncode != 0:
        files = sorted(set(re.findall(r"(?:^|\\s)((?:core|tests|scripts)/[A-Za-z0-9_./-]+\\.py)", result.stdout + "\\n" + result.stderr)))
        files = files[:8]
        task = (
            "آزمون روزانهٔ SIMORGH شکست خورده است. کم‌خطرترین اصلاح قابل‌آزمون را پیشنهاد بده. "
            "هیچ patch را بدون آزمون و تأیید انسانی اعمال نکن. خروجی فقط unified diff باشد.\\n\\n"
            + payload["stdout"][-6000:]
            + "\\n\\n"
            + payload["stderr"][-6000:]
        )
        try:
            proposal = propose_patch(ledger, task, files or ["main.py"])
        except Exception as exc:
            proposal = {"status": "NOT_AVAILABLE", "error": type(exc).__name__}
    return {"quality": payload, "repair_proposal": proposal}
