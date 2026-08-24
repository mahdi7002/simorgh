import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "simorgh"))
from core.stt import transcribe

EXCLUDE_DIRS = {"venv", "node_modules", ".git", "__pycache__", ".cache"}
EXTS = {".wav", ".mp3", ".m4a", ".ogg"}
OUT_DIR = Path.home() / "simorgh" / "transcripts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def main():
    home = Path.home()
    for ext in EXTS:
        for f in home.rglob(f"*{ext}"):
            if should_skip(f):
                continue
            out_txt = OUT_DIR / (f.stem + ".txt")
            if out_txt.exists():
                continue
            try:
                text = transcribe(str(f))
                out_txt.write_text(text, encoding="utf-8")
                print(f"✓ {f} -> {out_txt.name} ({len(text)} کاراکتر)")
            except Exception as e:
                print(f"✗ {f} -> خطا: {e}")

if __name__ == "__main__":
    main()
