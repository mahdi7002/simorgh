#!/usr/bin/env python3
"""Model-free orthographic invariance check for the locked 30-pair v1 fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "eval" / "normalization_pairs_v1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verse_text(prompt: str) -> str:
    match = re.search(r"«(.*?)»", prompt, flags=re.DOTALL)
    if not match:
        raise ValueError("poetry pair has no guillemet-quoted verse")
    return match.group(1)


def signature_poetry(module, prompt: str) -> tuple[dict, bool]:
    result = module.lookup(verse_text(prompt))
    status = result.get("status", "UNKNOWN")
    if status == "answer":
        signature = {"status": status, "pid": result.get("pid")}
        return signature, True
    if status in {"ambiguous", "uncertain"}:
        candidates = sorted(result.get("cand_pids") or [])
        signature = {"status": status, "candidate_pids": candidates}
        return signature, bool(candidates)
    return {"status": status}, False


def signature_quran(module, prompt: str) -> tuple[list, bool]:
    rows = module.get_quran_wisdom(prompt, limit=5)
    signature = [
        {"surah": str(row.get("surah", "")),
         "ayah": str(row.get("ayah", "")),
         "text": str(row.get("text", ""))}
        for row in rows
    ]
    return signature, bool(signature)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    raw = args.fixture.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8"))
    pairs = payload["pairs"]
    counts = Counter(item["category"] for item in pairs)
    expected_counts = {
        "arabic_yeh": 6, "arabic_kaf": 6, "zwnj_vs_space": 6,
        "digit_forms": 6, "diacritics": 6,
    }
    if len(pairs) != 30 or counts != Counter(expected_counts):
        print("FIXTURE_GATE=FAIL")
        print("pair_count=", len(pairs), "category_counts=", dict(counts))
        return 2
    if len({item["id"] for item in pairs}) != 30:
        print("FIXTURE_GATE=FAIL duplicate IDs")
        return 2
    if any(item.get("expected_invariant") is not True for item in pairs):
        print("FIXTURE_GATE=FAIL missing locked expectation")
        return 2

    # Print the immutable fixture hash before running the first query.
    print(f"FIXTURE={args.fixture}")
    print(f"FIXTURE_SHA256={digest}")
    print(f"FIXTURE_STATUS={payload.get('_status')}")
    print(f"FIXTURE_PAIR_COUNT={len(pairs)}")
    print(f"FIXTURE_CATEGORY_COUNTS={json.dumps(dict(counts), ensure_ascii=False, sort_keys=True)}", flush=True)

    verse_path = Path(os.environ.get(
        "SIMORGH_VERSE_DB", str(ROOT / "data" / "poetry" / "persian_poetry.db")
    )).expanduser().resolve()
    quran_path = Path(os.environ.get(
        "SIMORGH_QURAN_DB", str(ROOT / "data" / "grid" / "quran.db")
    )).expanduser().resolve()
    for label, path in (("verse", verse_path), ("quran", quran_path)):
        if not path.is_file():
            print(f"{label.upper()}_DB_STATUS=MISSING path={path}")
            return 3
        with path.open("rb") as fh:
            if fh.read(40).startswith(b"version https://git-lfs"):
                print(f"{label.upper()}_DB_STATUS=GIT_LFS_POINTER_NOT_DATA path={path}")
                return 3
        print(f"{label.upper()}_DB_SHA256={sha256_file(path)}")

    from core import quran_search
    from app.knowledge import poetry_lookup

    per_pair = []
    for pair in pairs:
        engine = pair["engine"]
        if engine == "poetry_lookup":
            left, left_hit = signature_poetry(poetry_lookup, pair["left"])
            right, right_hit = signature_poetry(poetry_lookup, pair["right"])
        elif engine == "quran_search":
            left, left_hit = signature_quran(quran_search, pair["left"])
            right, right_hit = signature_quran(quran_search, pair["right"])
        else:
            raise ValueError(f"unsupported engine {engine!r}")
        per_pair.append({
            "id": pair["id"], "category": pair["category"], "engine": engine,
            "stable": left == right, "left_hit": left_hit, "right_hit": right_hit,
            "left_signature": left, "right_signature": right,
        })

    grouped = {}
    for category in expected_counts:
        rows = [row for row in per_pair if row["category"] == category]
        grouped[category] = {
            "pairs": len(rows),
            "stable": sum(row["stable"] for row in rows),
            "left_hits": sum(row["left_hit"] for row in rows),
            "right_hits": sum(row["right_hit"] for row in rows),
            "no_hit_on_both": sum(not row["left_hit"] and not row["right_hit"] for row in rows),
        }
    result = {
        "timestamp_local": datetime.now().astimezone().isoformat(),
        "fixture": str(args.fixture), "fixture_sha256": digest,
        "criterion": payload["_criterion"], "database_sha256": {
            "verse_db": sha256_file(verse_path), "quran_db": sha256_file(quran_path)
        },
        "pair_count": len(per_pair), "stable_count": sum(r["stable"] for r in per_pair),
        "groups": grouped, "pairs": per_pair,
        "note": "Model-free retrieval invariance only. Stable empty results count as invariant, not as successful retrieval or correct attribution.",
    }
    out = args.out
    if out is None:
        out_dir = Path.home() / "simorgh-joint-audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"normalization-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("=== MODEL-FREE NORMALIZATION RESULT ===")
    print(f"PAIR_COUNT={len(per_pair)}")
    print(f"STABLE_COUNT={result['stable_count']}/{len(per_pair)}")
    print("GROUPS=" + json.dumps(grouped, ensure_ascii=False, sort_keys=True))
    print(f"RESULT_JSON={out}")
    print("ACCURACY_CLAIM=NOT_MADE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
