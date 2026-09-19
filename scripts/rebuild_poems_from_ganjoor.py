#!/usr/bin/env python3
"""Build a complete SIMORGH poetry database from a pinned Ganjoor snapshot.

The source is fetched into a local cache, parsed read-only, and written to a
staging SQLite database. The canonical database is changed only with --apply.
Before replacement, the old database is copied to a timestamped backup.

Completeness policy: preserve one SQLite row per parsed Ganjoor poem JSON file.
No default text-length filter, no content-based deduplication, and empty-text
records are preserved. Runtime consumers may impose prompt/display limits later.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REF = "a64968e78425b2e8c7904fbdf5289fba8251a757"
DEFAULT_SOURCE = "https://github.com/ganjoor/ganjoor-data.git"
DEFAULT_MAX_CHARS = 0
BATCH = 1000


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
        )
        if text:
            return text
    sections = poem.get("Sections") or []
    return "\n".join(
        str(s.get("PlainText", "")).strip()
        for s in sections
        if isinstance(s, dict)
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


def load_manifest(source_dir: Path) -> dict[str, Any]:
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("PoemsCount") is None or manifest.get("PoetsCount") is None:
        raise SystemExit("Ganjoor manifest is missing required counts")
    return manifest


def iter_poem_files(source_dir: Path):
    root = source_dir / "poets"
    if not root.is_dir():
        raise SystemExit(f"Ganjoor poets directory missing: {root}")
    for path in root.rglob("*.json"):
        if path.name not in {"poet.json", "_cat.json"}:
            yield path


def load_poet_map(manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for poet in manifest.get("Poets", []):
        full = str(poet.get("FullUrl", "")).strip("/")
        slug = full.split("/")[-1] if full else ""
        if slug and poet.get("Nickname"):
            out[slug] = str(poet["Nickname"])
    return out


def recreate_poetry_layer(target: Path, rows: list[tuple[str, str, str, str]]) -> tuple[int, int]:
    with sqlite3.connect(target) as conn:
        fts_sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='poems_fts'"
        ).fetchone()
        fts_sql = fts_sql_row[0] if fts_sql_row else None
        conn.execute("DROP TABLE IF EXISTS poems_fts")
        conn.execute("DROP TABLE IF EXISTS poems")
        conn.execute(
            "CREATE TABLE poems (id INTEGER PRIMARY KEY AUTOINCREMENT, poet TEXT, title TEXT, text TEXT, source TEXT)"
        )
        inserted = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            if not batch:
                continue
            conn.executemany(
                "INSERT INTO poems(poet,title,text,source) VALUES (?,?,?,?)",
                batch,
            )
            inserted += len(batch)
        if fts_sql:
            conn.execute(fts_sql)
        else:
            conn.execute(
                "CREATE VIRTUAL TABLE poems_fts USING fts5(poet, title, text, source, content='poems')"
            )
        conn.execute("INSERT INTO poems_fts(poems_fts) VALUES ('rebuild')")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity}")
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
    return inserted, count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/simorgh_full.db"))
    parser.add_argument("--output", type=Path, default=Path("rebuild_staging/ganjoor_simorgh_full.db"))
    parser.add_argument("--source-dir", type=Path, default=Path("rebuild_staging/ganjoor-data"))
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--remote", default=DEFAULT_SOURCE)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="0 disables the size filter")
    parser.add_argument("--apply", action="store_true", help="atomically replace --db after successful build and validation")
    args = parser.parse_args()

    repo = ensure_source(args.source_dir, args.ref, args.remote)
    manifest = load_manifest(repo)
    poet_map = load_poet_map(manifest)
    rows: list[tuple[str, str, str, str]] = []
    stats = {
        "manifest_poets": manifest["PoetsCount"],
        "manifest_poems": manifest["PoemsCount"],
        "files_seen": 0,
        "json_parsed": 0,
        "insertable": 0,
        "oversize_skipped": 0,
        "empty_text_preserved": 0,
        "unknown_poet": 0,
        "invalid_json": 0,
    }

    for path in iter_poem_files(repo):
        stats["files_seen"] += 1
        try:
            poem = json.loads(path.read_text(encoding="utf-8"))
            stats["json_parsed"] += 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            stats["invalid_json"] += 1
            continue
        if not isinstance(poem, dict):
            stats["invalid_json"] += 1
            continue
        parts = path.relative_to(repo / "poets").parts
        slug = parts[0]
        poet = poet_map.get(slug, slug)
        if slug not in poet_map:
            stats["unknown_poet"] += 1
        title = str(poem.get("Title") or poem.get("title") or path.stem).strip()
        text = poem_text(poem)
        if not text.strip():
            stats["empty_text_preserved"] += 1
        if args.max_chars > 0 and len(text) > args.max_chars:
            stats["oversize_skipped"] += 1
            continue
        poem_id = poem.get("Id") or poem.get("id") or path.stem
        rel = path.relative_to(repo).as_posix()
        source = f"ganjoor-data@{args.ref}#{poem_id}::{rel}"
        rows.append((poet, title, text, source))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()
    if not args.db.exists():
        raise SystemExit(f"Canonical DB not found: {args.db}")
    shutil.copy2(args.db, args.output)
    inserted, count = recreate_poetry_layer(args.output, rows)
    stats["insertable"] = inserted
    stats["final_rows"] = count

    metadata = {
        "source_repository": args.remote,
        "source_commit": args.ref,
        "generated_at_utc": manifest.get("GeneratedAtUtc"),
        "manifest_poets": manifest["PoetsCount"],
        "manifest_poems": manifest["PoemsCount"],
        "max_chars": args.max_chars,
        "completeness_target": "one SQLite row per Ganjoor poem JSON file",
        "stats": stats,
        "output": str(args.output),
        "non_destructive_build": not args.apply,
        "apply_requested": args.apply,
    }
    args.output.with_suffix(args.output.suffix + ".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False))
    print(f"STAGING DB: {args.output}")

    if args.apply:
        source = args.db.resolve()
        backup = source.with_name(source.name + ".pre_ganjoor_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".bak")
        shutil.copy2(source, backup)
        temp_apply = source.with_name(source.name + ".ganjoor.tmp")
        shutil.copy2(args.output, temp_apply)
        os.replace(temp_apply, source)
        print(f"BACKUP: {backup}")
        print(f"APPLIED: {source}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: external command failed with exit {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)
