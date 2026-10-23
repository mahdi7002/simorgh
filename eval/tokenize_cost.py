#!/usr/bin/env python3
"""Prepare one local-only 200-sentence sample and measure llama.cpp /tokenize."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sqlite3
import statistics
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = Path.home() / "simorgh-joint-audit" / "tokenize_sample_200.jsonl"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(40).startswith(b"version https://git-lfs")
    except OSError:
        return False


def prepare(db_path: Path, sample_path: Path, seed: int) -> int:
    if sample_path.exists():
        print("SAMPLE_EXISTS_NOT_OVERWRITTEN=YES")
        print(f"SAMPLE_PATH={sample_path}")
        print(f"SAMPLE_SHA256={sha256_file(sample_path)}")
        rows = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines() if line]
        print(f"SAMPLE_COUNT={len(rows)}")
        print("SAMPLE_REUSE=YES")
        return 0
    if not db_path.is_file():
        print(f"SAMPLE_PREPARE=NOT_MEASURED; DB_MISSING={db_path}")
        return 2
    if is_lfs_pointer(db_path):
        print(f"SAMPLE_PREPARE=NOT_MEASURED; DB_IS_LFS_POINTER={db_path}")
        return 2

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        contents = con.execute(
            "SELECT content FROM knowledge_fts "
            "WHERE source='قرآن' AND category='معنوی' ORDER BY rowid"
        ).fetchall()
    finally:
        con.close()

    rows = []
    for (content,) in contents:
        if not isinstance(content, str) or " | " not in content:
            continue
        prefix, text = content.split(" | ", 1)
        if not text.strip() or len(re.findall(r"\w+", text, flags=re.UNICODE)) < 6:
            continue
        match = re.search(r"سوره\s*(\d+)\s*آیه\s*(\d+)", prefix)
        rows.append({"surah": match.group(1) if match else "",
                     "ayah": match.group(2) if match else "",
                     "text": text.strip()})
    if len(rows) < 200:
        print(f"SAMPLE_PREPARE=NOT_MEASURED; eligible_rows={len(rows)}; required=200")
        return 2

    sample = random.Random(seed).sample(rows, 200)
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    raw = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in sample)
    # O_EXCL protects an existing artifact against accidental replacement.
    with sample_path.open("x", encoding="utf-8") as fh:
        fh.write(raw)
    print(f"SAMPLE_PATH={sample_path}")
    print(f"SAMPLE_COUNT={len(sample)}")
    print(f"SAMPLE_SEED={seed}")
    print(f"SOURCE_DB={db_path}")
    print(f"SOURCE_DB_SHA256={sha256_file(db_path)}")
    print(f"SAMPLE_SHA256={sha256_file(sample_path)}")
    print("SAMPLE_SCOPE=local research only; do not publish or redistribute the sentence file")
    return 0


def process_rss_bytes(pid: int | None) -> int | None:
    if pid is None:
        return None
    try:
        import psutil
        return psutil.Process(pid).memory_info().rss
    except Exception:
        try:
            status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
            match = re.search(r"^VmRSS:\s+(\d+)\s+kB$", status, re.MULTILINE)
            return int(match.group(1)) * 1024 if match else None
        except OSError:
            return None


def measure(sample_path: Path, url: str, model_path: Path, label: str, pid: int | None, out_dir: Path) -> int:
    if not sample_path.is_file():
        print(f"TOKENIZE_STATUS=NOT_MEASURED; sample missing: {sample_path}")
        return 2
    if not model_path.is_file():
        print(f"TOKENIZE_STATUS=NOT_MEASURED; model missing: {model_path}")
        return 2
    rows = [json.loads(line) for line in sample_path.read_text(encoding="utf-8").splitlines() if line]
    print(f"SAMPLE_PATH={sample_path}")
    print(f"SAMPLE_SHA256={sha256_file(sample_path)}")
    print(f"SAMPLE_COUNT={len(rows)}")
    print(f"MODEL_LABEL={label}")
    print(f"MODEL_PATH={model_path}")
    print(f"MODEL_SHA256={sha256_file(model_path)}")
    print(f"TOKENIZE_URL={url}")
    if len(rows) != 200:
        print("TOKENIZE_STATUS=NOT_MEASURED; locked sample must contain exactly 200 sentences")
        return 2

    results, before, peak, errors = [], process_rss_bytes(pid), None, []
    t0 = time.monotonic()
    for idx, row in enumerate(rows, 1):
        request_body = json.dumps(
            {"content": row["text"], "add_special": False, "parse_special": False},
            ensure_ascii=False,
        ).encode("utf-8")
        req = Request(url, data=request_body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            started = time.monotonic()
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            elapsed = time.monotonic() - started
            tokens = data.get("tokens")
            if not isinstance(tokens, list):
                raise ValueError("response has no 'tokens' array")
            words = len(re.findall(r"\w+", row["text"], flags=re.UNICODE))
            results.append({
                "index": idx, "surah": row.get("surah", ""), "ayah": row.get("ayah", ""),
                "characters": len(row["text"]), "words_regex_w": words,
                "token_count": len(tokens), "request_seconds": round(elapsed, 6),
            })
        except (OSError, HTTPError, URLError, ValueError, json.JSONDecodeError) as exc:
            errors.append({"index": idx, "error": f"{type(exc).__name__}: {exc}"})
            break
        rss = process_rss_bytes(pid)
        if rss is not None:
            peak = rss if peak is None else max(peak, rss)
        if idx % 50 == 0:
            print(f"TOKENIZE_PROGRESS={idx}/200", flush=True)

    duration = time.monotonic() - t0
    after = process_rss_bytes(pid)
    if errors or len(results) != 200:
        print("TOKENIZE_STATUS=NOT_MEASURED")
        print("ERRORS=" + json.dumps(errors, ensure_ascii=False))
        return 3

    total_tokens = sum(r["token_count"] for r in results)
    total_words = sum(r["words_regex_w"] for r in results)
    token_counts = [r["token_count"] for r in results]
    result = {
        "timestamp_local": datetime.now().astimezone().isoformat(),
        "model_label": label, "model_path": str(model_path),
        "model_sha256": sha256_file(model_path), "endpoint": url,
        "sample_path": str(sample_path), "sample_sha256": sha256_file(sample_path),
        "sample_count": len(results), "seed": "locked in sample file",
        "add_special": False, "parse_special": False,
        "word_count_definition": "len(re.findall(r'\\w+', sentence, re.UNICODE))",
        "total_tokens": total_tokens, "total_words": total_words,
        "tokens_per_word": round(total_tokens / total_words, 4) if total_words else None,
        "mean_tokens_per_sentence": round(statistics.mean(token_counts), 3),
        "median_tokens_per_sentence": statistics.median(token_counts),
        "total_request_seconds": round(duration, 3),
        "server_pid": pid, "rss_before_bytes": before, "rss_after_bytes": after,
        "rss_peak_sampled_bytes": peak, "rows": results,
        "scope_note": "Local non-commercial research measurement. This sample contains Quran translation text; do not redistribute it.",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"tokenize-cost-{re.sub(r'[^A-Za-z0-9_-]+','_',label)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("TOKENIZE_STATUS=MEASURED")
    print(f"SENTENCES={len(results)}")
    print(f"TOTAL_TOKENS={total_tokens}")
    print(f"TOTAL_WORDS_REGEX_W={total_words}")
    print(f"TOKENS_PER_WORD={result['tokens_per_word']}")
    print(f"MEAN_TOKENS_PER_SENTENCE={result['mean_tokens_per_sentence']}")
    print(f"MEDIAN_TOKENS_PER_SENTENCE={result['median_tokens_per_sentence']}")
    print(f"ELAPSED_SECONDS={round(duration, 3)}")
    print(f"RSS_PEAK_SAMPLED_BYTES={peak if peak is not None else 'NOT_MEASURED'}")
    print(f"RESULT_JSON={path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--db", type=Path, default=Path(__import__("os").environ.get(
        "SIMORGH_QURAN_DB", str(ROOT / "data" / "grid" / "quran.db")
    )))
    prep.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    prep.add_argument("--seed", type=int, default=20261012)
    run = sub.add_parser("measure")
    run.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    run.add_argument("--url", default="http://127.0.0.1:8080/tokenize")
    run.add_argument("--model-file", type=Path, required=True)
    run.add_argument("--label", required=True)
    run.add_argument("--server-pid", type=int, default=None)
    run.add_argument("--out-dir", type=Path, default=Path.home() / "simorgh-joint-audit")
    args = parser.parse_args()
    if args.cmd == "prepare":
        return prepare(args.db.expanduser().resolve(), args.sample.expanduser().resolve(), args.seed)
    return measure(args.sample.expanduser().resolve(), args.url, args.model_file.expanduser().resolve(),
                   args.label, args.server_pid, args.out_dir.expanduser().resolve())


if __name__ == "__main__":
    raise SystemExit(main())
