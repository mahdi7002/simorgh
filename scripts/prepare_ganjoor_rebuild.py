#!/usr/bin/env python3
"""Prepare a non-destructive candidate rebuild from Ganjoor public data.

The tool accepts either the historical local JSON quarantine backup or a
quarantine table in SQLite. It never mutates canonical data. It resolves
poet/title pairs against a pinned ganjoor-data snapshot, reconstructs matched
poems, validates text-size constraints, and writes a reviewable JSON candidate.

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
    value = str(value or "").strip().replace("\u200c", " ")
    value = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.replace("ي", "ی").replace("ك", "ک").casefold()


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", norm(value))


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


def load_quarantine_db(db_path: Path, table: str) -> list[dict[str, Any]]:
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
    return [dict(zip(columns, row)) for row in rows]


def load_quarantine_json(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read quarantine JSON {path}: {exc}") from exc

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("quarantine") or payload.get("items")
    else:
        rows = None

    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise SystemExit(
            "Quarantine JSON must be a list of objects or an object containing "
            "a 'rows', 'quarantine', or 'items' list."
        )
    return rows


def load_input(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    if args.input_json:
        return load_quarantine_json(args.input_json), "json"
    return load_quarantine_db(args.db, args.table), "sqlite"


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
            key = norm(title)
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


def generic_title(title: str) -> bool:
    key = norm(title)
    return key in {
        "مجموعه اشعار",
        "غزلیات",
        "اشعار",
        "قصاید",
        "قطعات",
        "رباعیات",
    }


def text_similarity_score(source: str, target: str) -> int:
    """Cheap evidence score, based on long exact normalized fragments."""
    a = compact_text(source)
    b = compact_text(target)
    if not a or not b:
        return 0
    probes = []
    if len(a) >= 80:
        probes.append(a[:80])
        probes.append(a[-80:])
    elif len(a) >= 30:
        probes.append(a[:30])
    return sum(len(p) for p in probes if p and p in b)


def resolve_by_text(
    ref: str,
    slug: str,
    title_map: dict[str, list[dict[str, Any]]],
    source_text: str,
    timeout: float,
    max_candidates: int = 8,
) -> list[dict[str, Any]]:
    """Fetch candidate poems and rank exact long-fragment matches.

    This is deliberately evidence-based: no fuzzy acceptance threshold is used
    to silently choose a poem. Callers receive ranked candidates and must review
    ties or weak evidence.
    """
    scored: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for entries in title_map.values():
        for entry in entries:
            url = upstream_url(ref, f"poets{entry['full_url']}.json")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            poem = fetch_json(url, timeout)
            text = poem_text(poem)
            score = text_similarity_score(source_text, text)
            if score:
                scored.append(
                    {
                        "title": entry["title"],
                        "full_url": entry["full_url"],
                        "id": poem.get("Id"),
                        "score": score,
                        "text_chars": len(text),
                    }
                )
    scored.sort(key=lambda item: (item["score"], -item["text_chars"]), reverse=True)
    return scored[:max_candidates]


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input-json",
        type=Path,
        help="historical local quarantine JSON backup; read-only",
    )
    group.add_argument(
        "--db",
        type=Path,
        help="local SQLite database; opened read-only",
    )
    parser.add_argument("--table", default="poems_quarantine")
    parser.add_argument("--output", type=Path, required=True, help="candidate JSON; never the canonical DB")
    parser.add_argument("--ref", default=DEFAULT_REF, help="pinned ganjoor-data commit SHA")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument(
        "--enable-text-fallback",
        action="store_true",
        help="for unresolved generic titles, fetch poet poems and produce ranked text-evidence candidates",
    )
    args = parser.parse_args()

    rows, input_kind = load_input(args)
    if not rows:
        raise SystemExit("Quarantine input is empty")

    columns = list(rows[0].keys())
    poet_col = choose_column(columns, ("poet", "poet_name", "author", "nickname"))
    title_col = choose_column(columns, ("title", "poem_title", "name", "subject"))
    text_col = choose_column(columns, ("text", "body", "content", "poem_text"))
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
        "text_fallback_candidates": 0,
        "text_fallback_ambiguous": 0,
    }

    for row_index, row in enumerate(rows, start=1):
        poet = str(row.get(poet_col, "")).strip()
        title = str(row.get(title_col, "")).strip()
        original_text = str(row.get(text_col, "")).strip() if text_col else ""
        item: dict[str, Any] = {
            "quarantine_row": row_index,
            "input_id": row.get("id"),
            "poet": poet,
            "title": title,
            "input_reason": row.get("reason"),
            "input_source": row.get("source"),
            "input_text_chars": len(original_text),
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

        if not matches and args.enable_text_fallback and generic_title(title) and original_text:
            ranked = resolve_by_text(
                args.ref,
                slug,
                crawl_cache[slug],
                original_text,
                timeout=20.0,
            )
            if ranked:
                item["status"] = "TEXT_FALLBACK_REVIEW"
                item["text_matches"] = ranked
                stats["text_fallback_candidates"] += 1
                if len(ranked) > 1 and ranked[0]["score"] == ranked[1]["score"]:
                    stats["text_fallback_ambiguous"] += 1
                candidates.append(item)
                continue

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
        "schema_version": 2,
        "tool": "SIMORGH prepare_ganjoor_rebuild",
        "input": {"kind": input_kind, "path": str(args.input_json or args.db)},
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
    review_keys = (
        "ambiguous",
        "missing_poet",
        "missing_title",
        "oversize",
        "text_fallback_candidates",
    )
    return 0 if all(stats[key] == 0 for key in review_keys) else 2


if __name__ == "__main__":
    raise SystemExit(main())
