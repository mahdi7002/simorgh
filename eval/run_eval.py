#!/usr/bin/env python3
"""Reproducible SIMORGH evaluation: one command -> JSON + Markdown table.

    python eval/run_eval.py                 # offline sections + LLM if reachable
    python eval/run_eval.py --no-llm        # offline sections only
    SIMORGH_LLM_URL=http://127.0.0.1:8080/v1/chat/completions python eval/run_eval.py

Sections
  A. smalltalk guard      greetings must not trigger retrieval (deterministic)
  B. quran retrieval      EASY setting: query = verse text from the DB itself, seeded sample
  C. poetry availability  real DB vs Git-LFS pointer, topical hit rate
  D. LLM QA               qa / abstain / classify items, latency + tokens/sec (needs endpoint)
Every number is tagged with its setting; nothing is estimated.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import database_answer, quran_search  # noqa: E402
from core import poetry_search  # noqa: E402

GREETING_CASES = ["سلام", "درود", "سلام ممنون", "ممنون", "خداحافظ", "چطوری", "hi", "صبح بخیر", "درود، خوبی؟", "مرسی"]
TOPIC_CASES = ["صبر چیست", "عدالت چیست", "سلام عدالت چیست", "درباره توکل بگو", "معنی رحمت", "سلام، صبر را توضیح بده"]
POETRY_TOPICS = ["عشق", "صبر", "وطن", "مرگ", "باده", "امید", "دوست", "جهان", "عدالت", "خرد"]


def env_info() -> dict:
    cpu = platform.processor() or ""
    try:
        for line in open("/proc/cpuinfo", encoding="utf-8"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    try:
        import psutil
        ram = round(psutil.virtual_memory().total / 2**30, 1)
    except Exception:
        ram = None
    try:
        commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    return {"cpu": cpu, "cores": os.cpu_count(), "ram_gb": ram, "python": platform.python_version(),
            "os": platform.platform(), "commit": commit}


def section_smalltalk() -> dict:
    ok_greet = sum(database_answer.is_smalltalk(q) for q in GREETING_CASES)
    ok_topic = sum(not database_answer.is_smalltalk(q) for q in TOPIC_CASES)
    reply_ok = all(database_answer.build_database_answer(q) == (database_answer.SMALLTALK_REPLY, []) for q in GREETING_CASES)
    return {"setting": "deterministic, hand-written cases", "greetings_blocked": f"{ok_greet}/{len(GREETING_CASES)}",
            "topics_not_blocked": f"{ok_topic}/{len(TOPIC_CASES)}", "no_sources_on_greeting": reply_ok}


def section_quran(n: int, seed: int) -> dict:
    db = quran_search.DB_PATH
    if not db.is_file():
        return {"status": "SKIPPED", "reason": f"missing {db}"}
    with closing(sqlite3.connect(db)) as conn:
        rows = conn.execute("select content from knowledge_fts where category='معنوی'").fetchall()
    verses = []
    for (content,) in rows:
        m = re.match(r"سوره\s*(\d+)\s*آیه\s*(\d+)\s*\|\s*(.*)", content.strip())
        if m and len(quran_search._extract_keywords(m.group(3))) >= 2:
            verses.append((m.group(1), m.group(2), m.group(3).strip()))
    rng = random.Random(seed)
    sample = rng.sample(verses, min(n, len(verses)))
    hits1 = hitsk = 0
    k = 10
    for surah, ayah, text in sample:
        res = quran_search.get_quran_wisdom(text, limit=k)
        keys = [(r["surah"], r["ayah"]) for r in res]
        hitsk += (surah, ayah) in keys
        hits1 += bool(keys) and keys[0] == (surah, ayah)
    return {"setting": f"EASY: query = the verse's own text, seed={seed}, n={len(sample)}, db rows={len(rows)}",
            "top1": f"{hits1}/{len(sample)}", f"top{k}": f"{hitsk}/{len(sample)}"}


def section_poetry() -> dict:
    db = poetry_search.DB_PATH
    if not db.is_file():
        return {"status": "SKIPPED", "reason": "poetry DB missing"}
    if poetry_search._is_lfs_pointer(db):
        return {"status": "SKIPPED", "reason": "poetry DB is a Git LFS pointer — run: git lfs pull"}
    hit = sum(bool(poetry_search.get_poetic_wisdom(t, limit=2)) for t in POETRY_TOPICS)
    return {"setting": "topical keyword retrieval, non-empty rate only (not correctness)", "nonempty": f"{hit}/{len(POETRY_TOPICS)}"}


def llm_chat(url: str, prompt: str, timeout: int) -> dict:
    import requests
    body = {"messages": [{"role": "system", "content": "فقط فارسی و کوتاه پاسخ بده. اگر نمی‌دانی صریح بگو «نمی‌دانم»."},
                         {"role": "user", "content": prompt}], "max_tokens": 120, "temperature": 0}
    t0 = time.time()
    r = requests.post(url, json=body, timeout=timeout)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    toks = (data.get("usage") or {}).get("completion_tokens")
    return {"text": text, "seconds": dt, "tokens": toks, "model": data.get("model")}


def section_llm(url: str, questions_path: Path, timeout: int) -> dict:
    import requests
    try:
        requests.get(url.rsplit("/v1/", 1)[0] + "/health", timeout=5).raise_for_status()
    except Exception as exc:
        return {"status": "SKIPPED", "reason": f"no reachable endpoint at {url}: {type(exc).__name__}"}
    items = json.loads(questions_path.read_text(encoding="utf-8"))["items"]
    per, lat, tps = [], [], []
    model = None
    for it in items:
        try:
            out = llm_chat(url, it["prompt"], timeout)
        except Exception as exc:
            per.append({"id": it["id"], "type": it["type"], "pass": False, "error": type(exc).__name__})
            continue
        model = model or out["model"]
        ans = out["text"].replace("\u200c", " ")
        needles = [x.replace("\u200c", " ") for x in it["expected_any"]]
        per.append({"id": it["id"], "type": it["type"], "pass": any(x in ans for x in needles),
                    "answer": out["text"][:160], "seconds": round(out["seconds"], 1)})
        lat.append(out["seconds"])
        if out["tokens"]:
            tps.append(out["tokens"] / out["seconds"])
    by_type = {}
    for p in per:
        a = by_type.setdefault(p["type"], [0, 0])
        a[0] += p["pass"]
        a[1] += 1
    return {"setting": f"questions file: {questions_path.name}, temperature 0, max_tokens 120", "model": model,
            "by_type": {k: f"{v[0]}/{v[1]}" for k, v in by_type.items()},
            "latency_s_median": round(statistics.median(lat), 1) if lat else None,
            "tokens_per_s_median": round(statistics.median(tps), 1) if tps else None, "items": per}


def to_markdown(report: dict) -> str:
    e, s = report["env"], report["sections"]
    lines = [f"# SIMORGH evaluation — {report['timestamp']}", "",
             f"Environment: {e['cpu']} · {e['cores']} threads · {e['ram_gb']} GB RAM · Python {e['python']} · commit `{e['commit']}`", "",
             "| Section | Setting | Result |", "|---|---|---|"]
    a = s["smalltalk_guard"]
    lines.append(f"| A. Smalltalk guard | {a['setting']} | greetings blocked {a['greetings_blocked']}; topics kept {a['topics_not_blocked']}; no sources on greeting: {a['no_sources_on_greeting']} |")
    q = s["quran_retrieval"]
    lines.append("| B. Quran retrieval | " + q.get("setting", q.get("reason", "")) + " | " + (", ".join(f"{k} {v}" for k, v in q.items() if k.startswith("top")) or q.get("status", "")) + " |")
    p = s["poetry"]
    lines.append("| C. Poetry DB | " + p.get("setting", p.get("reason", "")) + " | " + p.get("nonempty", p.get("status", "")) + " |")
    l = s["llm_qa"]
    if l.get("status") == "SKIPPED":
        lines.append(f"| D. LLM QA | {l['reason']} | SKIPPED |")
    else:
        res = ", ".join(f"{k} {v}" for k, v in l["by_type"].items())
        lines.append(f"| D. LLM QA | model {l['model']}; {l['setting']} | {res}; median {l['latency_s_median']} s, {l['tokens_per_s_median']} tok/s |")
    lines += ["", "Notes: B is an easy setting (self-retrieval) and measures regression, not real-world accuracy. "
              "C measures availability only. D uses a small starter question set; report its size alongside any claim.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--questions", type=Path, default=ROOT / "eval" / "questions.json")
    ap.add_argument("--url", default=os.environ.get("SIMORGH_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions"))
    ap.add_argument("--quran-n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    report = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "env": env_info(), "sections": {}}
    report["sections"]["smalltalk_guard"] = section_smalltalk()
    report["sections"]["quran_retrieval"] = section_quran(args.quran_n, args.seed)
    report["sections"]["poetry"] = section_poetry()
    report["sections"]["llm_qa"] = ({"status": "SKIPPED", "reason": "--no-llm"} if args.no_llm
                                    else section_llm(args.url, args.questions, args.timeout))

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out_dir / f"{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(report)
    (ROOT / "eval" / "RESULTS.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
