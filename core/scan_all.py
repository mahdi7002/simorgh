import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "simorgh"))
from core.doc_import import import_file

EXCLUDE_DIRS = {"venv", "node_modules", ".git", "__pycache__", ".cache", "site-packages"}
EXTS = {".txt", ".pdf", ".md"}

def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def main():
    home = Path.home()
    total = 0
    for ext in EXTS:
        for f in home.rglob(f"*{ext}"):
            if should_skip(f):
                continue
            try:
                count = import_file(str(f))
                total += count
                print(f"✓ {f} -> {count} قطعه")
            except Exception as e:
                print(f"✗ {f} -> خطا: {e}")
    print(f"\nمجموع قطعات ایندکس‌شده: {total}")

if __name__ == "__main__":
    main()
