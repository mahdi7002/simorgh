import json, hashlib
from pathlib import Path

def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    catalog_path = Path.home() / "simorgh" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    docs = catalog["standalone_docs"]

    seen_hashes = {}
    unique_docs = []
    for d in docs:
        try:
            h = file_hash(d)
        except (OSError, PermissionError):
            continue
        if h not in seen_hashes:
            seen_hashes[h] = d
            unique_docs.append(d)

    catalog["standalone_docs_unique"] = unique_docs
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"قبل از حذف تکراری: {len(docs)}")
    print(f"بعد از حذف تکراری: {len(unique_docs)}")

if __name__ == "__main__":
    main()
