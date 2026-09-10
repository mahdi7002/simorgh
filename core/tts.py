import subprocess, uuid
from pathlib import Path

MODEL = str(Path.home() / "simorgh/models/piper/fa_IR-gyro-medium.onnx")
OUT_DIR = Path.home() / "simorgh" / "audio_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def synthesize(text: str) -> str:
    out_path = OUT_DIR / f"{uuid.uuid4().hex}.wav"
    proc = subprocess.run(
        ["/home/mahdi/.local/bin/piper", "--model", MODEL, "--output_file", str(out_path)],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))
    return str(out_path)
