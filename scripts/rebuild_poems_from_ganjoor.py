#!/usr/bin/env python3
"""Build a clean SIMORGH poetry database from a pinned ganjoor-data snapshot.

The source is fetched into a local cache, parsed read-only, and written to a
staging SQLite database. The canonical database is changed only with --apply.
Before replacement, the old database is copied to a timestamped backup.

This intentionally rebuilds the poetry layer from Ganjoor instead of trying to
repair historical concatenated/corrupted rows individually.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REF = "a64968e78425b2e8c7904fbdf5289fba8251a757"
DEFAULT_SOURCE = "https://github.com/ganjoor/ganjoor-data.git"
DEFAULT_MAX_CHARS = 3000
BATCH = 1000


def norm(value: str) -> str:
    return " ".join(str(value or "").strip().replace("\u200c", " ").split()).replace("ي", "ی").replace("ك", "ک").casefold()


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
    if (source_dir / ".git").exists():
        current = subprocess.check_output(
            ["git", "-C", str(source_dir), "rev-parse", "HEAD"], text=True
        ).strip()
        if current != ref:
            subprocess.run(["git", "-C", str(source_dir), "fetch", "--depth", "1", "origin", ref], check=True)
            subprocess.run(["git", "-C", str(source_dir), "checkout", "--detach", ref], check=True)
    else:
        source_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", remote, str(source_dir)], check=True)
        subprocess.run(["git", "-C", str(source_dir), "fetch", "--depth", "1", "origin", ref], check=True)
        subprocess.run(["git", "-C", str(source_dir), "checkout", "--detach", ref], check=True)
    actual = subprocess.check_output(["git", "-C", str(source_dir), "rev-parse", "HEAD"], text=True).strip()
    if actual != ref:
        raise SystemExit(f"Pinned Ganjoor ref mismatch: requested {ref}, got {actual}")
    return source_dir


def load_manifest(source_dir: Path, ref: str) -> dict[str, Any]:
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("PoemsCount") is None or manifest.get("PoetsCount") is None:
        raise SystemExit("Ganjoor manifest is missing required counts")
    return manifest


def iter_poem_files(source_dir: Path):
    poets_dir = source_dir / "poets"
    for path in poets_dir.rglob("*.json"):
        if path.name in {"poet.json", "_cat.json"}:
            continue
        yield path


def infer_poet_slug(source_dir: Path, path: Path) -> str:
    rel = path.relative_to(source_dir / "poets")
    return rel.parts[0]


def load_poet_map(manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for poet in manifest.get("Poets", []):
        full = str(poet.get("FullUrl", "")).strip("/")
        slug = full.split("/")[-1] if full else ""
        if slug and poet.get("Nickname"):
            out[slug] = str(poet["Nickname"])
    return out


def recreate_poetry_layer(target: Path, rows: list[tuple[str, str, str, str]]) -> tuple[int, int]:
    """Rebuild only poems + its FTS table inside a copied canonical DB."""
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
        seen: set[tuple[str, str, str]] = set()
        for i in range(0, len(rows), BATCH):
            batch = []
            for row in rows[i : i + BATCH]:
                key = (row[0], row[1], row[2])
                if key in seen:
                    continue
                seen.add(key)
                batch.append(row)
            if batch:
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
        try:
            conn.execute("INSERT INTO poems_fts(poems_fts) VALUES ('rebuild')")
        except sqlite3.DatabaseError:
            pass
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
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                        help="0 disables the size filter")
    parser.add_argument("--apply", action="store_true",
                        help="atomically replace --db after successful build and validation")
    parser.add_argument("--keep-source", action="store_true",
                        help="keep the local Ganjoor checkout; otherwise it remains in ignored staging")
    args = parser.parse_args()

    repo = ensure_source(args.source_dir.resolve(), args.ref, args.remote)
    manifest = load_manifest(repo, args.ref)
    poet_map = load_poet_map(manifest)

    rows: list[tuple[str, str, str, str]] = []
    stats = {
        "manifest_poets": manifest["PoetsCount"],
        "manifest_poems": manifest["PoemsCount"],
        "files_seen": 0,
        "json_parsed": 0,
        "insertable": 0,
        "oversize_skipped": 0,
        "empty_skipped": 0,
        "duplicate_skipped": 0,
        "unknown_poet": 0,
    }
    dedupe: set[tuple[str, str, str]] = set()

    for path in iter_poem_files(repo):
        stats["files_seen"] += 1
        try:
            poem = json.loads(path.read_text(encoding="utf-8"))
            stats["json_parsed"] += 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(poem, dict):
            continue
        slug = infer_poet_slug(repo, path)
        poet = poet_map.get(slug, slug)
        if slug not in poet_map:
            stats["unknown_poet"] += 1
        title = str(poem.get("Title") or poem.get("title") or path.stem).strip()
        text = poem_text(poem)
        if not text.strip():
            stats["empty_skipped"] += 1
            continue
        if args.max_chars > 0 and len(text) > args.max_chars:
            stats["oversize_skipped"] += 1
            continue
        key = (norm(poet), norm(title), norm(text))
        if key in dedupe:
            stats["duplicate_skipped"] += 1
            continue
        dedupe.add(key)
        poem_id = poem.get("Id") or poem.get("id") or path.stem
        rel = path.relative_to(repo).as_posix()
        source = f"ganjoor-data@{args.ref}#{poem_id}::{rel}"
        rows.append((poet, title, text, source))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()
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
        "stats": stats,
        "output": str(args.output),
        "non_destructive_build": not args.apply,
        "apply_requested": args.apply,
    }
    meta_path = args.output.with_suffix(args.output.suffix + ".json")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(metadata, ensure_ascii=False))
    print(f"STAGING DB: {args.output}")

    if args.apply:
        source = args.db.resolve()
        backup = source.with_name(
            source.name + ".pre_ganjoor_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".bak"
        )
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
