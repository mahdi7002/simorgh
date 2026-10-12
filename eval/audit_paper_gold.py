#!/usr/bin/env python3
"""Read-only gold-label gate for the fixed 40-item paper benchmark."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "eval" / "questions_paper_v1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(40).startswith(b"version https://git-lfs")


def norm(text: str) -> str:
    text = text.replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    text = "".join(c for c in unicodedata.normalize("NFKC", text)
                   if unicodedata.category(c) not in {"Mn", "Me", "Cf"})
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().lower()


def alias_match(expected: str, actual: str) -> bool:
    e, a = norm(expected), norm(actual)
    if not e or not a:
        return False
    if e in a or a in e:
        return True
    aliases = {"مولانا": {"مولانا", "مولوی"}, "مولوی": {"مولوی", "مولانا"}}
    return any(alias in a for alias in aliases.get(e, set()))


def audit_quran(items: list[dict], db_path: Path) -> list[dict]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    out = []
    try:
        for item in items:
            ref = item.get("source_ref", "")
            match = re.search(r"(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?", ref)
            if not match:
                out.append({"id": item["id"], "status": "NOT_VERIFIED", "reason": f"unparsed source_ref: {ref}"})
                continue
            surah, start = int(match.group(1)), int(match.group(2))
            end = int(match.group(3) or start)
            if not (1 <= surah <= 114 and 1 <= start <= end <= 300):
                out.append({"id": item["id"], "status": "NOT_VERIFIED", "reason": f"invalid coordinates: {ref}"})
                continue
            rows = []
            for ayah in range(start, end + 1):
                prefix = f"سوره {surah} آیه {ayah} | "
                got = con.execute(
                    "SELECT content FROM knowledge_fts "
                    "WHERE source='قرآن' AND category='معنوی' AND content LIKE ? ORDER BY rowid LIMIT 2",
                    (prefix + "%",),
                ).fetchall()
                if got:
                    rows.append({"ayah": ayah, "content": got[0][0]})
            combined = norm(" ".join(row["content"].split(" | ", 1)[-1] for row in rows))
            matched = [expected for expected in item.get("expected_any", []) if norm(expected) in combined]
            status = "PASS" if len(rows) == end - start + 1 and matched else "NOT_VERIFIED"
            out.append({
                "id": item["id"], "source_ref": ref, "status": status,
                "row_count": len(rows), "expected_phrase_match": matched,
                "rows": rows,
            })
    finally:
        con.close()
    return out


def audit_poetry(items: list[dict], module) -> list[dict]:
    db = module.get_db()
    out = []
    for item in items:
        match = re.search(r"«(.*?)»", item.get("prompt", ""), flags=re.DOTALL)
        if not match:
            out.append({"id": item["id"], "status": "NOT_VERIFIED", "reason": "no quoted verse"})
            continue
        quote = match.group(1)
        parts = [p.strip() for p in quote.split("/") if p.strip()]
        hits = []
        for part in parts:
            words = module.words(part)
            if len(words) < 3:
                continue
            query = '"' + " ".join(words[:12]) + '"'
            try:
                rows = module.fts(query, 100)
            except Exception:
                rows = []
            for (rid,) in rows:
                info = module.info(rid)
                if not info or module.words(info[5]) != words:
                    continue
                hit = {"matched_text": info[5], "poet": info[2], "poet_id": info[1]}
                if hit not in hits:
                    hits.append(hit)
        expected = item.get("expected_any", [])
        matched = sorted({
            hit["poet"] for hit in hits
            if any(alias_match(exp, hit["poet"]) for exp in expected)
        })
        out.append({
            "id": item["id"], "expected_any": expected,
            "status": "PASS" if matched else "NOT_VERIFIED",
            "matching_holders": matched,
            "exact_corpus_matches": hits,
        })
    return out


def main() -> int:
    payload = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    counts = Counter(item.get("type") for item in items)
    expected = Counter({
        "poetry_attribution": 10, "source_qa": 10, "abstain": 10, "classify": 10
    })
    print(f"QUESTIONS_SHA256={sha256_file(QUESTIONS)}")
    print(f"QUESTION_COUNT={len(items)}")
    print(f"CATEGORY_COUNTS={json.dumps(dict(counts), ensure_ascii=False, sort_keys=True)}")
    if len(items) != 40 or counts != expected:
        print("GOLD_GATE=BLOCKED; question set count/balance mismatch")
        return 2

    quran_path = Path(os.environ.get(
        "SIMORGH_QURAN_DB", str(ROOT / "data" / "grid" / "quran.db")
    )).expanduser().resolve()
    verse_path = Path(os.environ.get(
        "SIMORGH_VERSE_DB", str(ROOT / "data" / "poetry" / "persian_poetry.db")
    )).expanduser().resolve()
    for label, path in (("QURAN_DB", quran_path), ("VERSE_DB", verse_path)):
        print(f"{label}_PATH={path}")
        if not path.is_file():
            print(f"{label}_STATUS=MISSING")
            print("GOLD_GATE=BLOCKED")
            return 3
        if is_lfs_pointer(path):
            print(f"{label}_STATUS=GIT_LFS_POINTER_NOT_DATA")
            print("GOLD_GATE=BLOCKED")
            return 3
        print(f"{label}_SHA256={sha256_file(path)}")

    try:
        with sqlite3.connect(f"file:{quran_path}?mode=ro", uri=True, timeout=10) as con:
            con.execute("SELECT content FROM knowledge_fts LIMIT 1").fetchone()
    except Exception as exc:
        print(f"QURAN_DB_STATUS=NOT_READABLE:{type(exc).__name__}:{exc}")
        print("GOLD_GATE=BLOCKED")
        return 3
    try:
        con = sqlite3.connect(f"file:{verse_path}?mode=ro", uri=True, timeout=10)
        con.execute("SELECT 1 FROM verses LIMIT 1").fetchone()
        con.close()
    except Exception as exc:
        print(f"VERSE_DB_STATUS=NOT_READABLE:{type(exc).__name__}:{exc}")
        print("GOLD_GATE=BLOCKED")
        return 3

    source_results = audit_quran([i for i in items if i.get("type") == "source_qa"], quran_path)
    os.environ["SIMORGH_VERSE_DB"] = str(verse_path)
    from app.knowledge import poetry_lookup
    poetry_results = audit_poetry([i for i in items if i.get("type") == "poetry_attribution"], poetry_lookup)

    print("=== QURAN GOLD AUDIT (exact local rows) ===")
    for row in source_results:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    print("=== POETRY GOLD AUDIT (exact local verse records) ===")
    for row in poetry_results:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))

    source_ok = len(source_results) == 10 and all(r["status"] == "PASS" for r in source_results)
    poetry_ok = len(poetry_results) == 10 and all(r["status"] == "PASS" for r in poetry_results)
    print(f"QURAN_GOLD_PASS={source_ok}")
    print(f"POETRY_GOLD_PASS={poetry_ok}")
    print(f"GOLD_GATE={'PASS' if source_ok and poetry_ok else 'BLOCKED'}")
    if not (source_ok and poetry_ok):
        print("Scored model runs must not start until every failing label/reference is manually audited and a corrected, re-versioned question set is frozen.")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
