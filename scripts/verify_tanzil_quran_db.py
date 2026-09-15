#!/usr/bin/env python3
"""Verify quran.db against the official Tanzil fa.ansarian source."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import urllib.request

SOURCE_URL = "https://tanzil.net/trans/fa.ansarian"
EXPECTED_AYAHS = 6236


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "SIMORGH-Tanzil-Verifier/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def source_rows(raw: bytes) -> list[tuple[int, int, str]]:
    rows = []
    for lineno, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid source row {lineno}")
        rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def db_rows(path: str) -> list[tuple[int, int, str]]:
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT content FROM knowledge_fts WHERE source='قرآن' AND category='معنوی' ORDER BY rowid"
    ).fetchall()
    con.close()
    result = []
    for (content,) in rows:
        prefix, translation = content.split(" | ", 1)
        words = prefix.split()
        if len(words) != 4 or words[0] != "سوره" or words[2] != "آیه":
            raise ValueError(f"Invalid DB row: {content!r}")
        result.append((int(words[1]), int(words[3]), translation))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/grid/quran.db")
    parser.add_argument("--source-url", default=SOURCE_URL)
    args = parser.parse_args()

    source = source_rows(fetch(args.source_url))
    actual = db_rows(args.db)

    if len(source) != EXPECTED_AYAHS:
        print(f"FAIL: source has {len(source)} rows, expected {EXPECTED_AYAHS}")
        return 1
    if len(actual) != EXPECTED_AYAHS:
        print(f"FAIL: DB has {len(actual)} rows, expected {EXPECTED_AYAHS}")
        return 1

    mismatches = []
    for index, (expected, got) in enumerate(zip(source, actual), 1):
        if expected != got:
            mismatches.append((index, expected, got))
            if len(mismatches) >= 10:
                break

    if mismatches:
        print("FAIL: DB content does not exactly match Tanzil fa.ansarian")
        for index, expected, got in mismatches:
            print("MISMATCH", index)
            print(" EXPECTED", expected)
            print(" GOT     ", got)
        return 1

    print("TANZIL_EXACT_MATCH: PASS")
    print(f"SOURCE: {args.source_url}")
    print(f"ROWS: {len(actual)}")
    print(f"DB: {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
