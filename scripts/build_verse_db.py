#!/usr/bin/env python3
"""Build the SIMORGH verse database from a local copy of the Ganjoor data export.

Structure: poets -> books -> poems -> verses (one row per hemistich) with FTS5 indexes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BUILDER_VERSION = "2"
BAIT_SEP = "    "
_DIACRITICS = re.compile("[\u064B-\u0652\u0670]")
NORMALIZER_NOTE = ("Arabic yeh, alef maksura and kaf mapped to Persian letters; "
                   "tatweel and harakat removed; zero-width non-joiner replaced by a space")
SOURCE_REMOTE = "https://github.com/ganjoor/ganjoor-data"
CREDIT = ("Poems: Ganjoor (https://ganjoor.net), through its public data export " + SOURCE_REMOTE +
          ". Built locally by the user; not redistributed by SIMORGH. Check the terms of the source before redistributing.")

# Preserve Ganjoor's actual Position, while keeping the existing numeric side
# field compatible with current query consumers.
POSITION_SIDE = {
    "Right": 1,
    "CenteredVerse1": 1,
    "Single": 1,
    "Left": 2,
    "CenteredVerse2": 2,
}

SCHEMA = """
CREATE TABLE poets (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, century_hijri INTEGER, approx_ce_range TEXT,
    poem_count INTEGER DEFAULT 0, verse_count INTEGER DEFAULT 0);
CREATE TABLE books (
    id INTEGER PRIMARY KEY, poet_id INTEGER NOT NULL REFERENCES poets(id), title TEXT NOT NULL, UNIQUE(poet_id, title));
CREATE TABLE poems (
    id INTEGER PRIMARY KEY, poet_id INTEGER NOT NULL REFERENCES poets(id), book_id INTEGER NOT NULL REFERENCES books(id),
    title TEXT, full_text TEXT NOT NULL, verse_count INTEGER,
    source_path TEXT NOT NULL UNIQUE, source_full_title TEXT NOT NULL,
    source_category_title TEXT);
CREATE TABLE verses (
    id INTEGER PRIMARY KEY, poem_id INTEGER NOT NULL REFERENCES poems(id), poet_id INTEGER NOT NULL REFERENCES poets(id),
    verse_order INTEGER NOT NULL, bait_number INTEGER NOT NULL, position_in_bait INTEGER NOT NULL,
    text TEXT NOT NULL, text_normalized TEXT NOT NULL,
    source_vorder INTEGER NOT NULL, source_position TEXT NOT NULL,
    source_couplet_index INTEGER);
CREATE TABLE build_info (key TEXT PRIMARY KEY, value TEXT);
"""
INDEXES = """
CREATE INDEX idx_poems_book ON poems(book_id);
CREATE INDEX idx_poems_poet ON poems(poet_id);
CREATE INDEX idx_verses_poem ON verses(poem_id);
CREATE INDEX idx_verses_poet ON verses(poet_id);
CREATE VIRTUAL TABLE poems_fts USING fts5(title, full_text, content='poems', content_rowid='id');
CREATE VIRTUAL TABLE verses_fts USING fts5(text, text_normalized, content='verses', content_rowid='id');
"""


def normalize_for_index(text: str) -> str:
    s = (text or "").replace("\u064A", "\u06CC").replace("\u0649", "\u06CC").replace("\u0643", "\u06A9")
    s = s.replace("\u0640", "")
    s = _DIACRITICS.sub("", s)
    return s.replace("\u200c", " ")


def load_poets(source: Path):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    out = []
    for p in manifest.get("Poets", []):
        full = str(p.get("FullUrl", "")).strip("/")
        slug = full.split("/")[-1] if full else ""
        nick = p.get("Nickname")
        if slug and nick:
            out.append((slug, str(nick)))
    return out, manifest


def poem_files(poet_dir: Path):
    for path in sorted(poet_dir.rglob("*.json")):
        if path.name in ("poet.json", "_cat.json"):
            continue
        yield path


def _source_category_title(source_path: Path | None):
    if source_path is None:
        return None
    cat_path = Path(source_path).parent / "_cat.json"
    if not cat_path.is_file():
        return None
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    value = cat.get("Title")
    return value if isinstance(value, str) and value else None


def extract(poem: dict, poet_nick: str, source_path: Path | None = None):
    verses = [v for v in (poem.get("Verses") or []) if isinstance(v, dict)]

    def source_order(v):
        try:
            return int(v["VOrder"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"source verse lacks a valid integer VOrder: {v!r}"
            ) from exc

    verses.sort(key=source_order)
    rows = []
    last_bait = 0

    for v in verses:
        pos_name = v.get("Position")

        # These are not verse text and must never enter the poetry index.
        if pos_name in ("Comment", "Paragraph"):
            continue

        raw_value = v.get("Text", "")
        text = raw_value if isinstance(raw_value, str) else (
            "" if raw_value is None else str(raw_value)
        )

        if not text.strip():
            continue

        # Fail closed if the source begins using a position this builder
        # has not explicitly accounted for.
        if pos_name not in POSITION_SIDE:
            raise ValueError(
                f"unsupported Ganjoor Position {pos_name!r}; "
                f"VOrder={v.get('VOrder')!r}, Title={poem.get('Title')!r}"
            )

        vorder = source_order(v)
        couplet_raw = v.get("CoupletIndex")
        try:
            couplet_index = int(couplet_raw)
        except (TypeError, ValueError):
            couplet_index = None

        if couplet_index is not None:
            bait = couplet_index + 1
        elif POSITION_SIDE[pos_name] == 2 and last_bait:
            bait = last_bait
        else:
            bait = last_bait + 1

        last_bait = bait

        # Keep Text byte-for-byte at the Unicode string level. Whitespace
        # normalization is applied only to the separate search-index field.
        rows.append((
            text, bait, POSITION_SIDE[pos_name],
            vorder, pos_name, couplet_index
        ))

    if not rows:
        return None

    # Build displayed full_text in source order. Only consecutive source
    # rows with the same CoupletIndex-derived bait are joined as a couplet.
    bait_groups = []
    for text, bait, _side, _vorder, _position, _couplet in rows:
        if not bait_groups or bait_groups[-1][0] != bait:
            bait_groups.append((bait, []))
        bait_groups[-1][1].append(text)

    full_text = "\n".join(
        BAIT_SEP.join(texts) for _bait, texts in bait_groups
    )

    full_title = str(poem.get("FullTitle") or "")
    parts = [
        x.strip() for x in full_title.split(" \u00bb ") if x.strip()
    ]
    title = str(poem.get("Title") or (parts[-1] if parts else ""))

    # Prefer the actual parent category from _cat.json when present.
    # Fall back to the FullTitle breadcrumb for minimal/test exports.
    category_title = _source_category_title(source_path)
    suffix = " \u00bb " + title
    if title and full_title.endswith(suffix):
        breadcrumb = full_title[:-len(suffix)]
        if " \u00bb " in breadcrumb:
            derived_book = breadcrumb.rsplit(" \u00bb ", 1)[-1]
        else:
            derived_book = breadcrumb or poet_nick
    else:
        derived_book = parts[-2] if len(parts) >= 2 else poet_nick

    book = category_title or derived_book
    return book, title, full_text, rows, full_title, category_title


def build(source_dir, output, poets=None, log=print) -> dict:
    t0 = time.time()
    source, output = Path(source_dir).resolve(), Path(output)
    part = output.with_name(output.name + ".part")
    metadata = output.with_name(output.name + ".build.json")
    for label, candidate in (
        ("output", output),
        ("staging file", part),
        ("build metadata", metadata),
    ):
        if candidate.exists() or candidate.is_symlink():
            raise FileExistsError(
                f"refusing to overwrite existing {label}: {candidate}"
            )
    available, manifest = load_poets(source)
    wanted = None if (not poets or list(poets) == ["all"]) else set(poets)
    chosen = [(s, n) for s, n in available if wanted is None or s in wanted]
    if wanted is not None:
        missing = sorted(wanted - {s for s, _n in available})
        if missing:
            log("WARNING: not in the Ganjoor manifest: " + ", ".join(missing))
    if not chosen:
        raise SystemExit("no poets selected")
    output.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(part))
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.executescript(SCHEMA)
    cur = conn.cursor()
    books: dict = {}
    used: set = set()
    bad = total_poems = total_verses = n_poets = 0
    for slug, nick in chosen:
        pdir = source / "poets" / slug
        if not pdir.is_dir():
            continue
        name = nick if nick not in used else "%s (%s)" % (nick, slug)
        cur.execute("INSERT INTO poets(name) VALUES (?)", (name,))
        poet_id = cur.lastrowid
        n_poems = n_verses = 0
        for path in poem_files(pdir):
            try:
                poem = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                bad += 1
                continue
            got = extract(poem, nick, path)
            if got is None:
                continue
            book, title, full_text, rows, source_full_title, source_category_title = got
            source_rel_path = path.relative_to(source).as_posix()
            bkey = (poet_id, book)
            book_id = books.get(bkey)
            if book_id is None:
                cur.execute("INSERT INTO books(poet_id, title) VALUES (?, ?)", bkey)
                book_id = cur.lastrowid
                books[bkey] = book_id
            cur.execute(
                "INSERT INTO poems(poet_id, book_id, title, full_text, verse_count, "
                "source_path, source_full_title, source_category_title) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    poet_id, book_id, title, full_text, len(rows),
                    source_rel_path, source_full_title, source_category_title
                ),
            )
            poem_id = cur.lastrowid
            cur.executemany(
                "INSERT INTO verses(poem_id, poet_id, verse_order, bait_number, position_in_bait, "
                "text, text_normalized, source_vorder, source_position, source_couplet_index) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        poem_id, poet_id, i, bait, side,
                        text, normalize_for_index(text),
                        source_vorder, source_position, source_couplet
                    )
                    for i, (
                        text, bait, side, source_vorder,
                        source_position, source_couplet
                    ) in enumerate(rows, 1)
                ],
            )
            n_poems += 1
            n_verses += len(rows)
            total_poems += 1
            if total_poems % 5000 == 0:
                conn.commit()
                log("  %d poems, %d verses, %ds" % (total_poems, total_verses + n_verses, time.time() - t0))
        if n_poems == 0:
            cur.execute("DELETE FROM poets WHERE id = ?", (poet_id,))
            continue
        used.add(name)
        n_poets += 1
        total_verses += n_verses
        cur.execute("UPDATE poets SET poem_count = ?, verse_count = ? WHERE id = ?", (n_poems, n_verses, poet_id))
    conn.commit()
    log("indexing (full-text search)...")
    conn.executescript(INDEXES)
    conn.execute("INSERT INTO poems_fts(poems_fts) VALUES ('rebuild')")
    conn.execute("INSERT INTO verses_fts(verses_fts) VALUES ('rebuild')")
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip() or "unknown"
    info = {
        "builder_version": BUILDER_VERSION,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_remote": SOURCE_REMOTE,
        "source_commit": commit,
        "source_generated": str(manifest.get("GeneratedAt", "")),
        "poets": str(n_poets),
        "poems": str(total_poems),
        "verses": str(total_verses),
        "normalizer": NORMALIZER_NOTE,
        "source_fidelity": (
            "poems.source_path, source_full_title, source_category_title; "
            "verses.source_vorder, source_position, source_couplet_index; "
            "verses.text preserves the source Text string"
        ),
        "position_policy": (
            "Paragraph and Comment excluded; unknown nonempty Position values "
            "fail closed; Right/CenteredVerse1/Single map to side 1; "
            "Left/CenteredVerse2 map to side 2"
        ),
        "credit": CREDIT,
        "note": "century_hijri and approx_ce_range are NULL: the source export has no such fields",
    }
    conn.executemany("INSERT INTO build_info(key, value) VALUES (?, ?)", list(info.items()))
    conn.commit()
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        conn.close()
        raise SystemExit("integrity check failed; the output was not written")
    probe = conn.execute("SELECT text_normalized FROM verses LIMIT 1 OFFSET 7").fetchone() or conn.execute(
        "SELECT text_normalized FROM verses LIMIT 1"
    ).fetchone()
    words = re.findall(r"\w+", probe[0])[:3] if probe else []
    if len(words) >= 2:
        hit = conn.execute(
            "SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? LIMIT 1",
            ('"' + " ".join(words) + '"',),
        ).fetchone()
        if hit is None:
            conn.close()
            raise SystemExit("full-text probe failed; the output was not written")
    conn.close()
    os.replace(part, output)
    stats = {
        "poets": n_poets,
        "poems": total_poems,
        "verses": total_verses,
        "bad_files": bad,
        "seconds": round(time.time() - t0, 1),
        "bytes": output.stat().st_size,
        "source_commit": commit,
    }
    output.with_name(output.name + ".build.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the SIMORGH verse database from Ganjoor data.")
    ap.add_argument("--source-dir", type=Path, default=Path("rebuild_staging/ganjoor-data"))
    ap.add_argument("--output", type=Path, default=Path("data/poetry/persian_poetry.db"))
    ap.add_argument("--poets", default="all", help="all, or comma-separated Ganjoor poet slugs")
    ap.add_argument("--poets-file", type=Path, default=None, help="file with one slug per line")
    a = ap.parse_args(argv)
    if a.poets_file:
        poets = [ln.strip() for ln in a.poets_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        poets = [p.strip() for p in a.poets.split(",") if p.strip()]
    s = build(a.source_dir, a.output, poets)
    print(
        "BUILD_OK poets=%d poems=%d verses=%d seconds=%s size_mb=%d source=%s"
        % (s["poets"], s["poems"], s["verses"], s["seconds"], s["bytes"] // 1000000, s["source_commit"][:9])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
