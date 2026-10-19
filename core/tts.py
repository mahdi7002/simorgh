import math
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from core.paths import AUDIO_OUT_DIR, PIPER_BIN, PIPER_MODEL


def _find_piper():
    candidates = [PIPER_BIN, Path.home() / ".local/bin/piper"]
    which = shutil.which("piper")
    if which:
        candidates.append(Path(which))
    for candidate in candidates:
        if candidate and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def synthesize(text: str, length_scale: float = 1.0) -> str:
    try:
        scale = float(length_scale)
    except (TypeError, ValueError) as exc:
        raise ValueError("length_scale must be a number between 0.8 and 1.4") from exc
    if not math.isfinite(scale) or not 0.8 <= scale <= 1.4:
        raise ValueError("length_scale must be between 0.8 and 1.4")

    binary = _find_piper()
    if not binary:
        raise RuntimeError("Piper executable not found. Set SIMORGH_PIPER_BIN.")
    if not PIPER_MODEL.exists():
        raise RuntimeError(f"Piper model not found: {PIPER_MODEL}")
    AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AUDIO_OUT_DIR / f"{uuid.uuid4().hex}.wav"
    proc = subprocess.run(
        [binary, "--model", str(PIPER_MODEL), "--length-scale", f"{scale:g}", "--output_file", str(out_path)],
        input=text.encode("utf-8"), capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore") or "Piper failed")
    return str(out_path)
