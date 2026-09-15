#!/usr/bin/env python3
"""Verify a SIMORGH poetry SQLite rebuild against a pinned Ganjoor snapshot.

The verifier is intentionally independent of the rebuild database contents:
it walks the pinned JSON corpus, reconstructs expected poet/title/text values,
and compares every source path/id to the SQLite row carrying that provenance.
It also checks manifest/file/row counts, SQLite integrity, empty-text rows and
optional FTS row coverage.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_REF = "a64968e78425b2e8c7904fbdf5289fba8251a757"
DEFAULT_SOURCE = "https://github.com/ganjoor/ganjoor-data.git"


def poem_text(poem: dict[str, Any]) -> str:
    verses = poem.get("Verses") or []
    if verses:
        ordered = sorted(
            (v for v in verses if isinstance(v, dict)),
            key=lambda v: v.get("VOrder", 0),
        )
        text = "\n".join(
            str(v.get("Text", "")).strip()
            for v in ordered
            if str(v.get("Text", "")).strip()
        )
        if text:
            return text
    sections = poem.get("Sections") or []
    return "\n".join(
        str(s.get("PlainText", "")).strip()
        for s in sections
        if isinstance(s, dict) and str(s.get("PlainText", "")).strip()
    )


def ensure_source(source_dir: Path, ref: str, remote: str) -> Path:
    source_dir = source_dir.resolve()
    if not (source_dir / ".git").exists():
        source_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", remote, str(source_dir)], check=True)
    current = subprocess.check_output(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if current != ref:
        subprocess.run(
            ["git", "-C", str(source_dir), "fetch", "--depth", "1", "origin", ref],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(source_dir), "checkout", "--detach", ref],
            check=True,
        )
    actual = subprocess.check_output(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != ref:
        raise SystemExit(f"Pinned Ganjoor ref mismatch: requested {ref}, got {actual}")
    return source_dir


def load_poet_map(manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for poet in manifest.get("Poets", []):
        full = str(poet.get("FullUrl", "")).strip("/")
        slug = full.split("/")[-1] if full else ""
        if slug and poet.get("Nickname"):
            out[slug] = str(poet["Nickname"])
    return out


def iter_poem_files(source_dir: Path):
    root = source_dir / "poets"
    for path in root.rglob("*.json"):
        if path.name not in {"poet.json", "_cat.json"}:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, default=Path("rebuild_staging/ganjoor-data"))
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--remote", default=DEFAULT_SOURCE)
    parser.add_argument("--max-mismatches", type=int, default=20)
    args = parser.parse_args()

    repo = ensure_source(args.source_dir, args.ref, args.remote)
    manifest = json.loads((repo / "manifest.json").read_text(encoding="utf-8"))
    poet_map = load_poet_map(manifest)

    with sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            print(f"FAIL integrity={integrity}")
            return 1
        db_rows = {}
        for poet, title, text, source in conn.execute(
            "SELECT poet,title,text,source FROM poems"
        ):
            db_rows[source] = (poet, title, text)
        db_count = len(db_rows)
        empty_count = conn.execute(
            "SELECT COUNT(*) FROM poems WHERE text IS NULL OR trim(text)=''"
        ).fetchone()[0]
        fts_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='poems_fts'"
        ).fetchone() is not None
        fts_count = None
        if fts_exists:
            fts_count = conn.execute("SELECT COUNT(*) FROM poems_fts").fetchone()[0]

    files = 0
    parsed = 0
    invalid = 0
    unknown_poet = 0
    mismatches: list[str] = []
    expected_sources: set[str] = set()

    for path in iter_poem_files(repo):
        files += 1
        try:
            poem = json.loads(path.read_text(encoding="utf-8"))
            parsed += 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            invalid += 1
            if len(mismatches) < args.max_mismatches:
                mismatches.append(f"invalid_json:{path}:{exc}")
            continue
        if not isinstance(poem, dict):
            invalid += 1
            if len(mismatches) < args.max_mismatches:
                mismatches.append(f"invalid_object:{path}")
            continue
        rel = path.relative_to(repo).as_posix()
        parts = path.relative_to(repo / "poets").parts
        slug = parts[0]
        poet = poet_map.get(slug, slug)
        if slug not in poet_map:
            unknown_poet += 1
        title = str(poem.get("Title") or poem.get("title") or path.stem).strip()
        text = poem_text(poem)
        poem_id = poem.get("Id") or poem.get("id") or path.stem
        source = f"ganjoor-data@{args.ref}#{poem_id}::{rel}"
        expected_sources.add(source)
        row = db_rows.get(source)
        if row is None:
            if len(mismatches) < args.max_mismatches:
                mismatches.append(f"missing:{source}")
            continue
        if row != (poet, title, text):
            if len(mismatches) < args.max_mismatches:
                mismatches.append(
                    f"content:{source}: db={row!r} expected={(poet,title,text)!r}"
                )

    orphan_sources = set(db_rows) - expected_sources
    expected_count = int(manifest["PoemsCount"])
    ok = (
        files == expected_count == db_count == len(expected_sources)
        and parsed == files
        and invalid == 0
        and unknown_poet == 0
        and not mismatches
        and not orphan_sources
    )

    print(json.dumps({
        "source_commit": args.ref,
        "manifest_poems": expected_count,
        "files_seen": files,
        "json_parsed": parsed,
        "invalid_json": invalid,
        "unknown_poet": unknown_poet,
        "db_rows": db_count,
        "empty_text_rows": empty_count,
        "fts_rows": fts_count,
        "missing_or_mismatched": len(mismatches),
        "orphan_db_rows": len(orphan_sources),
        "status": "PASS" if ok else "FAIL",
    }, ensure_ascii=False, indent=2))
    if mismatches:
        print("MISMATCHES:")
        for item in mismatches:
            print(item)
    if orphan_sources and len(mismatches) < args.max_mismatches:
        print("ORPHANS:")
        for item in sorted(orphan_sources)[: args.max_mismatches - len(mismatches)]:
            print(item)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: external command failed with exit {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)
