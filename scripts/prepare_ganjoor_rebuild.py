#!/usr/bin/env python3
"""Prepare a non-destructive candidate rebuild from Ganjoor public data.

This tool NEVER modifies the source SQLite database. It reads a quarantine table
from a local copy, resolves poet/title pairs against a pinned ganjoor-data
snapshot, downloads the matched poem JSON, validates text-size constraints, and
writes a reviewable JSON candidate outside the canonical database.

Human review is required before any candidate is copied into shipped data.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

UPSTREAM_REPO = "https://raw.githubusercontent.com/ganjoor/ganjoor-data"
DEFAULT_REF = "a64968e78425b2e8c7904fbdf5289fba8251a757"
DEFAULT_MAX_CHARS = 3000
USER_AGENT = "SIMORGH/ganjoor-rebuild-review-tool"


def norm(value: str) -> str:
    value = value.strip().replace("\u200c", " ")
    value = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("ي", "ی").replace("ك", "ک")
    return value.casefold()


def fetch_json(url: str, timeout: float = 20.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def upstream_url(ref: str, relative: str) -> str:
    return f"{UPSTREAM_REPO}/{ref}/{relative.lstrip('/')}"


def choose_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    for column in columns:
        low = column.lower()
        if any(candidate in low for candidate in candidates):
            return column
    return None


def load_quarantine(db_path: Path, table: str) -> tuple[list[dict[str, Any]], list[str]]:
    uri = f"file:{db_path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        if table not in tables:
            raise SystemExit(
                f"Quarantine table {table!r} not found. Tables: {', '.join(tables)}"
            )
        info = connection.execute(f"PRAGMA table_info({table})").fetchall()
        columns = [row[1] for row in info]
        rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(zip(columns, row)) for row in rows], columns


def crawl_poet(ref: str, slug: str, timeout: float) -> dict[str, list[dict[str, Any]]]:
    """Return normalized poem-title -> all matching poem metadata for one poet."""
    seen_cats: set[str] = set()
    poems: dict[str, list[dict[str, Any]]] = {}
    queue = [f"poets/{slug}/_cat.json"]

    while queue:
        relative = queue.pop()
        if relative in seen_cats:
            continue
        seen_cats.add(relative)
        try:
            category = fetch_json(upstream_url(ref, relative), timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and relative == f"poets/{slug}/_cat.json":
                raise RuntimeError(f"Ganjoor root category missing for poet {slug!r}") from exc
            raise
        for child in category.get("ChildCats") or []:
            full_url = child.get("FullUrl")
            if full_url:
                queue.append(f"poets{full_url}/_cat.json")
        for poem in category.get("Poems") or []:
            full_url = poem.get("FullUrl")
            title = poem.get("Title")
            if not full_url or not title:
                continue
            key = norm(str(title))
            poems.setdefault(key, []).append(
                {"title": title, "full_url": full_url, "id": poem.get("Id")}
            )
    return poems


def poem_text(poem: dict[str, Any]) -> str:
    verses = poem.get("Verses") or []
    if verses:
        ordered = sorted(
            (verse for verse in verses if isinstance(verse, dict)),
            key=lambda verse: verse.get("VOrder", 0),
        )
        return "\n".join(
            str(verse.get("Text", "")).strip()
            for verse in ordered
            if str(verse.get("Text", "")).strip()
        )
    sections = poem.get("Sections") or []
    return "\n".join(
        str(section.get("PlainText", "")).strip()
        for section in sections
        if isinstance(section, dict) and str(section.get("PlainText", "")).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True, help="local SQLite database; opened read-only")
    parser.add_argument("--table", default="poems_quarantine")
    parser.add_argument("--output", type=Path, required=True, help="candidate JSON; never the canonical DB")
    parser.add_argument("--ref", default=DEFAULT_REF, help="pinned ganjoor-data commit SHA")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--sleep", type=float, default=0.05)
    args = parser.parse_args()

    rows, columns = load_quarantine(args.db, args.table)
    poet_col = choose_column(columns, ("poet", "poet_name", "author", "nickname"))
    title_col = choose_column(columns, ("title", "poem_title", "name", "subject"))
    if not poet_col or not title_col:
        raise SystemExit(
            "Cannot infer poet/title columns. "
            f"Columns: {', '.join(columns)}. Review schema before proceeding."
        )

    manifest = fetch_json(upstream_url(args.ref, "manifest.json"))
    poet_map = {
        norm(str(item.get("Nickname", ""))): {
            "slug": str(item.get("FullUrl", "")).strip("/").split("/")[-1],
            "name": item.get("Nickname"),
            "id": item.get("Id"),
        }
        for item in manifest.get("Poets", [])
        if item.get("Nickname") and item.get("FullUrl")
    }

    crawl_cache: dict[str, dict[str, list[dict[str, Any]]]] = {}
    candidates: list[dict[str, Any]] = []
    stats = {
        "rows": len(rows),
        "matched": 0,
        "ambiguous": 0,
        "missing_poet": 0,
        "missing_title": 0,
        "oversize": 0,
    }

    for row_index, row in enumerate(rows, start=1):
        poet = str(row.get(poet_col, "")).strip()
        title = str(row.get(title_col, "")).strip()
        item: dict[str, Any] = {
            "quarantine_row": row_index,
            "poet": poet,
            "title": title,
            "upstream_ref": args.ref,
            "upstream_url": None,
            "upstream_id": None,
            "status": "UNRESOLVED",
            "text": None,
            "text_chars": None,
        }
        poet_info = poet_map.get(norm(poet))
        if poet_info is None:
            item["status"] = "MISSING_POET"
            stats["missing_poet"] += 1
            candidates.append(item)
            continue
        slug = poet_info["slug"]
        if slug not in crawl_cache:
            crawl_cache[slug] = crawl_poet(args.ref, slug, timeout=20.0)
        matches = crawl_cache[slug].get(norm(title), [])
        if not matches:
            item["status"] = "MISSING_TITLE"
            stats["missing_title"] += 1
            candidates.append(item)
            continue
        if len(matches) != 1:
            item["status"] = "AMBIGUOUS_TITLE"
            item["matches"] = matches
            stats["ambiguous"] += 1
            candidates.append(item)
            continue

        match = matches[0]
        url = upstream_url(args.ref, f"poets{match['full_url']}.json")
        poem = fetch_json(url)
        text = poem_text(poem)
        item.update(
            {
                "upstream_url": url,
                "upstream_id": poem.get("Id"),
                "text": text,
                "text_chars": len(text),
            }
        )
        if len(text) > args.max_chars:
            item["status"] = "OVERSIZE"
            stats["oversize"] += 1
        else:
            item["status"] = "MATCHED"
            stats["matched"] += 1
        candidates.append(item)
        time.sleep(max(args.sleep, 0.0))

    output = {
        "schema_version": 1,
        "tool": "SIMORGH prepare_ganjoor_rebuild",
        "source_repository": "ganjoor/ganjoor-data",
        "source_commit": args.ref,
        "source_manifest": {
            "generated_at": manifest.get("GeneratedAtUtc"),
            "poets": manifest.get("PoetsCount"),
            "poems": manifest.get("PoemsCount"),
        },
        "max_chars": args.max_chars,
        "non_destructive": True,
        "human_review_required": True,
        "stats": stats,
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    print(f"Candidate written: {args.output}")
    return 0 if all(stats[key] == 0 for key in ("ambiguous", "missing_poet", "missing_title", "oversize")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
