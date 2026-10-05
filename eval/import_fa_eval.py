#!/usr/bin/env python3
"""Convert a personal benchmark (JSONL or JSON list) into eval/questions format.

    python eval/import_fa_eval.py ~/Desktop/fa-eval/bench.jsonl            # writes eval/questions_fa_eval.json
    python eval/import_fa_eval.py bench.jsonl --dry-run                    # only show the mapping

Field names are detected flexibly; if none match, the script prints the keys it saw and exits with an error
instead of guessing. Run the result with:  python eval/run_eval.py --questions eval/questions_fa_eval.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

Q_KEYS = ("prompt", "question", "q", "input", "query", "text")
A_KEYS = ("expected_any", "expected", "answer", "answers", "gold", "label", "target", "a")
TYPE_KEYS = ("type", "task", "kind", "category")
ABSTAIN_WORDS = ("abstain", "unanswerable", "unknown", "نمی‌دانم")


def load_records(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8").strip()
    if raw.startswith("["):
        return [r for r in json.loads(raw) if isinstance(r, dict)]
    return [json.loads(line) for line in raw.splitlines() if line.strip().startswith("{")]


def first_key(rec: dict, keys) -> str | None:
    return next((k for k in keys if k in rec and rec[k] not in (None, "", [])), None)


def convert(records: list[dict]) -> tuple[list[dict], list[int]]:
    items, skipped = [], []
    for i, rec in enumerate(records, 1):
        qk, ak = first_key(rec, Q_KEYS), first_key(rec, A_KEYS)
        if not qk or not ak:
            skipped.append(i)
            continue
        ans = rec[ak]
        expected = [str(x) for x in ans] if isinstance(ans, list) else [str(ans)]
        tk = first_key(rec, TYPE_KEYS)
        typ = str(rec[tk]).lower() if tk else "qa"
        if any(w in typ for w in ABSTAIN_WORDS):
            typ, expected = "abstain", expected + ["نمی‌دانم", "نمی دانم", "اطلاعی ندارم"]
        elif "class" in typ:
            typ = "classify"
        else:
            typ = "qa"
        items.append({"id": f"fa-{i:03d}", "type": typ, "prompt": str(rec[qk]), "expected_any": expected})
    return items, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("questions_fa_eval.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    records = load_records(args.src)
    items, skipped = convert(records)
    if not items:
        seen = sorted({k for r in records[:5] for k in r}) if records else []
        print(f"ERROR: no record had both a question key {Q_KEYS} and an answer key {A_KEYS}. Keys seen: {seen}")
        return 1
    by_type = {}
    for it in items:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    print(f"mapped {len(items)}/{len(records)} records {by_type}; skipped lines: {skipped or 'none'}")
    print("example:", json.dumps(items[0], ensure_ascii=False))
    if not args.dry_run:
        args.out.write_text(json.dumps({"_note": f"imported from {args.src.name}", "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("written:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
