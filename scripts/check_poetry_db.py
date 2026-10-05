#!/usr/bin/env python3
"""Check that SIMORGH's poetry database is a real SQLite file, not a Git LFS pointer.

Usage:  python scripts/check_poetry_db.py [path ...]
Exit 0 = all checked files usable, 1 = problem found.
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = [ROOT / "data" / "simorgh_full.db", ROOT / "data" / "poetry" / "persian_poetry.db"]
POINTER_MAGIC = b"version https://git-lfs"


def parse_pointer(path: Path) -> dict[str, str] | None:
    head = path.read_bytes()[:512]
    if not head.startswith(POINTER_MAGIC):
        return None
    info = {}
    for line in head.decode("utf-8", "replace").splitlines():
        if " " in line:
            key, value = line.split(" ", 1)
            info[key] = value.strip()
    return info


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(path: Path) -> bool:
    print(f"== {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    if not path.is_file():
        print("   MISSING (file not present)")
        return False
    pointer = parse_pointer(path)
    if pointer:
        size_mb = int(pointer.get("size", "0")) / 1e6
        print(f"   LFS POINTER, not the real database ({size_mb:.0f} MB expected)")
        print("   fix:  git lfs install && git lfs pull")
        return False
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
            print(f"   OK sqlite, {len(tables)} tables: {', '.join(tables[:10])}")
            for name in ("poems", "verses", "poems_fts", "verses_fts"):
                if name in tables:
                    count = conn.execute(f"select count(*) from {name}").fetchone()[0]
                    print(f"   {name}: {count} rows")
    except sqlite3.DatabaseError as exc:
        print(f"   NOT A VALID SQLITE FILE: {exc}")
        return False
    print(f"   sha256: {sha256_file(path)}")
    return True


def main(argv: list[str]) -> int:
    paths = [Path(a).resolve() for a in argv] or [p for p in DEFAULTS if p.exists() or p == DEFAULTS[0]]
    results = [check(p) for p in paths]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
