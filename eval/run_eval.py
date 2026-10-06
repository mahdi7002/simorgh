#!/usr/bin/env python3
"""Reproducible SIMORGH evaluation: one command -> JSON + Markdown table.

    python eval/run_eval.py                 # offline sections + LLM if reachable
    python eval/run_eval.py --no-llm        # offline sections only
    SIMORGH_LLM_URL=http://127.0.0.1:8080/v1/chat/completions python eval/run_eval.py

Sections
  A. smalltalk guard      greetings must not trigger retrieval (deterministic)
  B. quran retrieval      EASY setting: query = verse text from the DB itself, seeded sample
  C. poetry availability  real DB vs Git-LFS pointer, topical hit rate
  E. verse attribution    who wrote this verse? deterministic lookup, coverage / accuracy / chimera false-accept
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


ABSTAIN_PHRASES = ("نمی‌دانم", "نمی دانم", "اطلاعی ندارم", "اطلاعاتی ندارم", "مطمئن نیستم", "نمی‌توانم")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n, as percentages."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5
    return round(100 * (c - a) / d, 1), round(100 * (c + a) / d, 1)


def env_info() -> dict:
    cpu = platform.processor() or ""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
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



def _load_lookup(path: str | None):
    import importlib
    import importlib.util
    if not path:
        return importlib.import_module("app.knowledge.poetry_lookup")
    spec = importlib.util.spec_from_file_location("alt_poetry_lookup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def same_text_poets(mod, text: str) -> set:
    """All poets holding this verse (same normalised words). The DB lists some verses under several poets
    (e.g. a quotation), so the ground truth for such a verse is a set, not a single poet."""
    ws = mod.words(text)
    try:
        rows = mod.fts('"' + " ".join(ws[:12]) + '"', 25)
    except Exception:
        return set()
    out = set()
    for (rid,) in rows:
        h = mod.info(rid)
        if h and mod.words(h[5]) == ws:
            out.add(h[1])
    return out


def draw_sample(mod, db, n: int, seed: int) -> list:
    """Seeded random verses (poet_id, text) with at least 6 words. Sequential RNG, so a smaller n is a prefix of a larger n."""
    lo, hi = db.execute("select min(id), max(id) from verses").fetchone()
    rng = random.Random(seed)
    sample, tries = [], 0
    while len(sample) < n and tries < n * 50:
        tries += 1
        row = db.execute("select v.poet_id, v.text from verses v where v.id=?", (rng.randint(lo, hi),)).fetchone()
        if row and len(mod.words(row[1])) >= 6:
            sample.append(row)
    return sample


def section_attribution(n: int, seed: int, lookup_file: str | None) -> dict:
    """Who wrote this verse? Deterministic lookup, no LLM. EASY setting: query = first words of an indexed verse."""
    try:
        mod = _load_lookup(lookup_file)
        db = mod.get_db() if hasattr(mod, "get_db") else mod.db
    except Exception as exc:
        return {"status": "SKIPPED", "reason": f"{type(exc).__name__}: {exc}"}
    sample = draw_sample(mod, db, n, seed)
    def drop_last_letter(ws):
        out = list(ws)
        for i in (2, 3, 1, 0):
            if i < len(out) and len(out[i]) >= 4:
                out[i] = out[i][:-1]
                break
        return out

    def drop_middle_letter(ws):
        out = list(ws[:6])
        for i in (2, 3, 1, 0):
            if i < len(out) and len(out[i]) >= 4:
                m = len(out[i]) // 2
                out[i] = out[i][:m] + out[i][m + 1:]
                break
        return out

    def swap_adjacent(ws):
        out = list(ws[:6])
        for i in (2, 3, 1, 0):
            if i < len(out) and len(out[i]) >= 4:
                m = len(out[i]) // 2 - 1
                w = list(out[i])
                w[m], w[m + 1] = w[m + 1], w[m]
                out[i] = "".join(w)
                break
        return out

    queries = {
        "prefix6": lambda ws: ws[:6],
        "middle4": lambda ws: ws[2:6],
        "typo": lambda ws: drop_last_letter(ws[:6]),
        "typo_mid": drop_middle_letter,
        "swap": swap_adjacent,
    }
    def poet_name(pid):
        row = db.execute("select name from poets where id=?", (pid,)).fetchone()
        return row[0] if row else str(pid)

    errors = []  # error analysis: every wrong answer and every accepted chimera, for the evidence file
    scored = {}
    for name, make in queries.items():
        answered = correct = in_cands = abstained = dup_ok = 0
        for pid, text in sample:
            query = " ".join(make(mod.words(text)))
            r = mod.lookup(query)
            if r["status"] == "answer":
                answered += 1
                if r["pid"] == pid:
                    correct += 1
                elif r["pid"] in same_text_poets(mod, text):
                    dup_ok += 1
                    if len(errors) < 50:
                        errors.append({"variant": name, "kind": "duplicate", "query": query, "true_poet": poet_name(pid),
                                       "true_verse": text, "got_poet": r["poet"], "got_verse": r["verse"]})
                elif len(errors) < 50:
                    errors.append({"variant": name, "kind": "wrong", "query": query, "true_poet": poet_name(pid), "true_verse": text,
                                   "got_poet": r["poet"], "got_verse": r["verse"]})
            else:
                abstained += 1
                in_cands += pid in r["cand_pids"]
        scored[name] = (answered, correct, abstained, in_cands, dup_ok)
    raw_counts = {name: {"answered": a, "correct": c, "abstained": ab, "in_candidates": ic, "dup_ok": d, "n": len(sample)}
                  for name, (a, c, ab, ic, d) in scored.items()}
    raw_counts["chimera"] = None  # filled below
    answered, correct, abstained, in_cands, _dup = scored["prefix6"]
    chim_n = chim_acc = 0
    for (pa, ta), (pb, tb) in zip(sample[::2], sample[1::2]):
        if pa == pb:
            continue
        chim_n += 1
        chim_query = " ".join(mod.words(ta)[:3] + mod.words(tb)[-3:])
        r = mod.lookup(chim_query)
        if r["status"] == "answer":
            chim_acc += 1
            if len(errors) < 50:
                errors.append({"variant": "chimera", "kind": "chimera", "got_poet_is_source": r["pid"] in (pa, pb), "query": chim_query, "true_poet": f"{poet_name(pa)} + {poet_name(pb)}",
                               "true_verse": f"{ta} + {tb}", "got_poet": r["poet"], "got_verse": r["verse"]})
    total = len(sample)
    return {"setting": f"EASY: query = first 6 words of a random indexed verse, seed={seed}, n={total}; lookup={lookup_file or 'app.knowledge.poetry_lookup'}",
            "coverage_answered": f"{answered}/{total}",
            "answered_accuracy": f"{correct + _dup}/{answered}" if answered else "n/a",
            "abstained_poet_in_candidates": f"{in_cands}/{abstained}" if abstained else "n/a",
            "chimera_false_accept": f"{chim_acc}/{chim_n}",
            "errors": errors,
            "counts": {**{k: v for k, v in raw_counts.items() if v}, "chimera": {"accepted": chim_acc, "n": chim_n}},
            "harder_variants": {
                name: {"answered": f"{a}/{total}", "answered_accuracy": f"{c + d}/{a}" if a else "n/a",
                       "abstained_poet_in_candidates": f"{ic}/{ab}" if ab else "n/a"}
                for name, (a, c, ab, ic, d) in scored.items() if name != "prefix6"}}


def llm_chat(url: str, prompt: str, timeout: int, max_tokens: int = 120) -> dict:
    import requests
    body = {"messages": [{"role": "system", "content": "فقط فارسی و کوتاه پاسخ بده. اگر نمی‌دانی صریح بگو «نمی‌دانم»."},
                         {"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": 0}
    t0 = time.time()
    r = requests.post(url, json=body, timeout=timeout)
    dt = time.time() - t0
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    toks = (data.get("usage") or {}).get("completion_tokens")
    return {"text": text, "seconds": dt, "tokens": toks, "model": data.get("model"), "tps": (data.get("timings") or {}).get("predicted_per_second")}


def _norm_name(text: str) -> str:
    text = text.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).strip().lower()


def name_match(answer: str, poet_name: str) -> bool:
    """Lenient on purpose (favours the LLM): full name contained either way, or any name token of 4+ letters appears."""
    a, n = _norm_name(answer), _norm_name(poet_name)
    if not a or not n:
        return False
    if n in a or (len(a) >= 3 and a in n):
        return True
    return any(len(tok) >= 4 and tok in a for tok in n.split())


def section_llm_baseline(n: int, seed: int, url: str, lookup_file: str | None, timeout: int) -> dict:
    """Same sample, same 6-word query: LLM alone (no retrieval) vs the deterministic lookup."""
    import requests
    try:
        mod = _load_lookup(lookup_file)
        db = mod.get_db() if hasattr(mod, "get_db") else mod.db
    except Exception as exc:
        return {"status": "SKIPPED", "reason": f"{type(exc).__name__}: {exc}"}
    try:
        requests.get(url.rsplit("/v1/", 1)[0] + "/health", timeout=5).raise_for_status()
    except Exception as exc:
        return {"status": "SKIPPED", "reason": f"no reachable endpoint at {url}: {type(exc).__name__}"}
    names = dict(db.execute("select id, name from poets").fetchall())
    sample = draw_sample(mod, db, n, seed)
    c = {"llm_correct": 0, "llm_abstained": 0, "llm_wrong": 0, "lookup_answered": 0, "lookup_correct": 0}
    secs, model, examples = [], None, []
    for pid, text in sample:
        query = " ".join(mod.words(text)[:6])
        holders = {pid} | same_text_poets(mod, text)
        try:
            out = llm_chat(url, f"این عبارت آغاز بیتی از شعر کلاسیک فارسی است: «{query}». سراینده‌اش کیست؟ فقط نام شاعر را بنویس.", timeout, 40)
        except Exception:
            continue
        model = model or out["model"]
        secs.append(out["seconds"])
        if any(name_match(out["text"], names.get(h, "")) for h in holders):
            c["llm_correct"] += 1
        elif any(a.replace("\u200c", " ") in out["text"] for a in ABSTAIN_PHRASES):
            c["llm_abstained"] += 1
        else:
            c["llm_wrong"] += 1
            if len(examples) < 5:
                examples.append({"query": query, "true": names.get(pid), "llm": out["text"][:60]})
        r = mod.lookup(query)
        if r["status"] == "answer":
            c["lookup_answered"] += 1
            c["lookup_correct"] += r["pid"] in holders
    total = c["llm_correct"] + c["llm_abstained"] + c["llm_wrong"]
    return {"setting": f"same sample and same 6-word query for both; n={total}, seed={seed}; LLM name matching is lenient (favours the LLM)",
            "model": model, "n": total, **c, "latency_s_median": round(statistics.median(secs), 1) if secs else None,
            "llm_wrong_examples": examples}


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
        ok = any(x in ans for x in needles)
        outcome = "correct" if ok else ("abstained" if any(a.replace("\u200c", " ") in ans for a in ABSTAIN_PHRASES) else "wrong")
        per.append({"id": it["id"], "type": it["type"], "pass": ok, "outcome": outcome,
                    "answer": out["text"][:160], "seconds": round(out["seconds"], 1)})
        lat.append(out["seconds"])
        if out.get("tps"):
            tps.append(out["tps"])
    by_type = {}
    for p in per:
        a = by_type.setdefault(p["type"], [0, 0])
        a[0] += p["pass"]
        a[1] += 1
    qa = [x for x in per if x["type"] == "qa" and "outcome" in x]
    breakdown = {k: sum(x["outcome"] == k for x in qa) for k in ("correct", "abstained", "wrong")}
    return {"setting": f"questions file: {questions_path.name}, temperature 0, max_tokens 120", "model": model,
            "by_type": {k: f"{v[0]}/{v[1]}" for k, v in by_type.items()}, "qa_breakdown": breakdown,
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
    a2 = s.get("verse_attribution", {})
    if a2.get("status") == "SKIPPED":
        lines.append(f"| E. Verse attribution | {a2['reason']} | SKIPPED |")
    elif a2:
        lines.append(f"| E. Verse attribution | {a2['setting']} | answered {a2['coverage_answered']}, answered-accuracy {a2['answered_accuracy']}, abstained-with-poet-in-candidates {a2['abstained_poet_in_candidates']}, chimera false-accepts {a2['chimera_false_accept']} |")
    labels = {"middle4": "middle 4 words (no prefix)", "typo": "prefix, last letter of a word dropped",
              "typo_mid": "prefix, a middle letter dropped", "swap": "prefix, two adjacent letters swapped"}
    for name, v in (a2.get("harder_variants", {}) if a2 else {}).items():
        lines.append(f"| E+. Verse attribution, {labels.get(name, name)} | same sample, same lookup | answered {v['answered']}, answered-accuracy {v['answered_accuracy']}, abstained-with-poet-in-candidates {v['abstained_poet_in_candidates']} |")
    b = s.get("llm_baseline", {})
    if b.get("status") == "SKIPPED":
        lines.append(f"| F. LLM alone vs lookup | {b['reason']} | SKIPPED |")
    elif b:
        nn = b["n"]
        lo1, hi1 = wilson(b["llm_correct"], nn)
        lines.append(f"| F. LLM alone vs lookup | model {b['model']}; {b['setting']} | LLM alone: {b['llm_correct']}/{nn} correct (CI {lo1}–{hi1}), "
                     f"{b['llm_abstained']} abstained, {b['llm_wrong']} WRONG; lookup: {b['lookup_answered']}/{nn} answered, {b['lookup_correct']}/{b['lookup_answered']} correct |")
    l = s["llm_qa"]
    if l.get("status") == "SKIPPED":
        lines.append(f"| D. LLM QA | {l['reason']} | SKIPPED |")
    else:
        res = ", ".join(f"{k} {v}" for k, v in l["by_type"].items())
        bd = l.get("qa_breakdown")
        if bd:
            res += f" (qa: {bd['correct']} correct / {bd['abstained']} abstained / {bd['wrong']} WRONG)"
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
    ap.add_argument("--attr-n", type=int, default=100)
    ap.add_argument("--baseline-n", type=int, default=100, help="LLM-alone vs lookup on the same verses (0 = skip)")
    ap.add_argument("--lookup-file", default=None, help="evaluate an alternative poetry_lookup.py instead of the repo module")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    report = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "env": env_info(), "sections": {}}
    report["sections"]["smalltalk_guard"] = section_smalltalk()
    report["sections"]["quran_retrieval"] = section_quran(args.quran_n, args.seed)
    report["sections"]["poetry"] = section_poetry()
    report["sections"]["verse_attribution"] = section_attribution(args.attr_n, args.seed, args.lookup_file)
    report["sections"]["llm_baseline"] = ({"status": "SKIPPED", "reason": "--no-llm or --baseline-n 0"} if (args.no_llm or args.baseline_n <= 0)
                                         else section_llm_baseline(args.baseline_n, args.seed, args.url, args.lookup_file, args.timeout))
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
