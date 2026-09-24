# -*- coding: utf-8 -*-
import os, shutil, subprocess, uuid
from pathlib import Path
from core.paths import ROOT, PIPER_BIN

MODEL = Path(os.environ.get("SIMORGH_PIPER_MODEL", str(ROOT / "models" / "piper" / "fa_IR-gyro-medium.onnx")))
OUT_DIR = Path(os.environ.get("SIMORGH_AUDIO_OUT", str(ROOT / "audio_out")))
OUT_DIR.mkdir(parents=True, exist_ok=True)

def available():
    return Path(PIPER_BIN).exists() or shutil.which("piper") is not None

def synthesize(text: str) -> str:
    if not available():
        raise RuntimeError("Piper not found")
    out = OUT_DIR / f"{uuid.uuid4().hex}.wav"
    bin_path = PIPER_BIN if Path(PIPER_BIN).exists() else (shutil.which("piper") or "piper")
    p = subprocess.run([bin_path, "--model", str(MODEL), "--output_file", str(out)],
                       input=text.encode("utf-8"), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", errors="ignore") or "piper failed")
    return str(out)
