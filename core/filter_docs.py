import json
from pathlib import Path

EXCLUDE_TOP = {".cargo", ".rustup", ".config", ".mozilla", ".local", ".thunderbird", ".claude", ".cache", ".npm"}
POETRY_DIR = "PoetryArchive"  # جدا نگه داشته می‌شه، نه حذف

def main():
    catalog_path = Path.home() / "simorgh" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    docs = catalog.get("standalone_docs_unique", catalog["standalone_docs"])
    home = str(Path.home())

    filtered = []
    poetry_docs = []
    for d in docs:
        rel = d[len(home)+1:] if d.startswith(home) else d
        top_dir = rel.split("/")[0]
        if top_dir in EXCLUDE_TOP:
            continue
        if top_dir == POETRY_DIR:
            poetry_docs.append(d)
            continue
        filtered.append(d)

    catalog["standalone_docs_filtered"] = filtered
    catalog["poetry_docs"] = poetry_docs
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"اسناد نهایی برای خلاصه‌سازی «مثل کتاب»: {len(filtered)}")
    print(f"اشعار (جدا نگه داشته شد، قبلاً در persian_poetry.db ایندکس‌ست): {len(poetry_docs)}")

if __name__ == "__main__":
    main()
