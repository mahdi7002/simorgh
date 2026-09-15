#!/usr/bin/env python3
"""Build SIMORGH's Persian Quran DB from the official Tanzil translation source.

This script intentionally treats Tanzil as a build-time source. The application does
not need network access at runtime. The downloaded translation is copied verbatim
into SQLite without editorial rewriting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import urllib.request
from pathlib import Path

SOURCE_URL = "https://tanzil.net/trans/fa.ansarian"
TRANSLATION_ID = "fa.ansarian"
TRANSLATOR_EN = "Hussain Ansarian"
TRANSLATOR_FA = "حسین انصاریان"
EXPECTED_AYAHS = 6236

HEADER = """# --------------------------------------------------------------------
#
#  Quran Translation
#  Name: انصاریان
#  Translator: Hussain Ansarian
#  Language: Persian
#  ID: fa.ansarian
#  Last Update: July 6, 2011
#  Source: Tanzil.net
#
# --------------------------------------------------------------------
"""


def download_source(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SIMORGH-Tanzil-Rebuilder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Tanzil source returned an empty response")
    return data


def parse_translation(raw: bytes) -> list[tuple[int, int, str]]:
    text = raw.decode("utf-8-sig")
    rows: list[tuple[int, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid Tanzil row at source line {lineno}: {line!r}")
        sura, aya, translation = parts
        try:
            rows.append((int(sura), int(aya), translation))
        except ValueError as exc:
            raise ValueError(f"Invalid aya coordinates at source line {lineno}") from exc
    if len(rows) != EXPECTED_AYAHS:
        raise ValueError(
            f"Expected {EXPECTED_AYAHS} translation rows from Tanzil, got {len(rows)}"
        )
    return rows


def build_db(rows: list[tuple[int, int, str]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        con = sqlite3.connect(tmp_path)
        con.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA foreign_keys=ON;
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE knowledge_fts USING fts5(
                source,
                category,
                content
            );
            """
        )
        metadata = {
            "domain": "قرآن کریم",
            "source": SOURCE_URL,
            "source_project": "Tanzil Project",
            "translation_id": TRANSLATION_ID,
            "translator": TRANSLATOR_EN,
            "translator_fa": TRANSLATOR_FA,
            "translation_last_update": "2011-07-06",
            "translation_terms": "Tanzil translations: non-commercial purposes only",
            "text_handling": "Verbatim translation rows from Tanzil; no SIMORGH editorial changes",
        }
        con.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            metadata.items(),
        )
        con.executemany(
            "INSERT INTO knowledge_fts(source, category, content) VALUES (?, ?, ?)",
            [
                ("قرآن", "معنوی", f"سوره {sura} آیه {aya} | {translation}")
                for sura, aya, translation in rows
            ],
        )
        con.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES ('optimize')")
        con.commit()
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        con.close()
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        tmp_path.replace(destination)
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/grid/quran.db",
        help="SQLite output path (default: data/grid/quran.db)",
    )
    parser.add_argument(
        "--source-url",
        default=SOURCE_URL,
        help="Tanzil translation URL; kept configurable for reproducible mirrors",
    )
    parser.add_argument(
        "--manifest",
        default="docs/TANZIL_FA_ANSARIAN_MANIFEST.json",
        help="Write source/build manifest JSON",
    )
    args = parser.parse_args()

    raw = download_source(args.source_url)
    rows = parse_translation(raw)
    output = Path(args.output)
    build_db(rows, output)

    source_sha256 = hashlib.sha256(raw).hexdigest()
    db_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "source_url": args.source_url,
        "translation_id": TRANSLATION_ID,
        "translator": TRANSLATOR_EN,
        "expected_ayah_rows": EXPECTED_AYAHS,
        "actual_ayah_rows": len(rows),
        "source_sha256": source_sha256,
        "sqlite_sha256": db_sha256,
        "output": str(output),
        "build_policy": "verbatim Tanzil translation rows; no editorial changes",
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"SOURCE: {args.source_url}")
    print(f"TRANSLATION: {TRANSLATION_ID} / {TRANSLATOR_EN}")
    print(f"ROWS: {len(rows)}")
    print(f"SOURCE_SHA256: {source_sha256}")
    print(f"DB_SHA256: {db_sha256}")
    print(f"OUTPUT: {output}")
    print(f"MANIFEST: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
