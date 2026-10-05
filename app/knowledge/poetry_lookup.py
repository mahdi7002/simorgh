import os
import re
import sqlite3
from pathlib import Path

# NOTE: deliberately NOT SIMORGH_POETRY_DB — core/poetry_search.py uses that name for a different database.
DB = os.environ.get(
    "SIMORGH_VERSE_DB",
    str(Path(__file__).resolve().parents[2] / "data" / "poetry" / "persian_poetry.db"),
)
_db = None


def get_db():
    """Open the verse database lazily, read-only. Raises a clear error instead of failing at import."""
    global _db
    if _db is None:
        path = Path(DB)
        if not path.is_file():
            raise FileNotFoundError(f"verse DB not found: {path}")
        with open(path, "rb") as fh:
            if fh.read(40).startswith(b"version https://git-lfs"):
                raise RuntimeError(f"{path} is a Git LFS pointer — run: git lfs pull")
        _db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    return _db


def close():
    global _db
    if _db is not None:
        _db.close()
        _db = None


STOP = set("از به در را که این آن با هم تا بر و ای من تو او ما شد بود هر یا نه".split())

def norm(s):
    s = s.replace("ي","ی").replace("ك","ک")
    return re.sub(r"[\u064B-\u065F\u0670]", "", s)
def words(s): return re.findall(r"\w+", norm(s))
def keep(ws):
    k = [w for w in ws if w not in STOP and len(w) >= 2]
    return k if len(k) >= 2 else ws
def fts(q, k):
    try:
        return get_db().execute("SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? ORDER BY bm25(verses_fts) LIMIT ?", (q, k)).fetchall()
    except sqlite3.OperationalError:
        return get_db().execute("SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? LIMIT ?", (q, k)).fetchall()
def info(rid):
    return get_db().execute("SELECT v.id,v.poet_id,p.name,v.poem_id,v.bait_number,v.text FROM verses v JOIN poets p ON p.id=v.poet_id WHERE v.id=?", (rid,)).fetchone()
def retrieve(ws, k=8):
    """Return (stage, hits, truncated). We fetch k+1 rows so a full result set reveals that the phrase is common
    and that the hits we see are only a sample of its occurrences."""
    rows = fts('"' + " ".join(ws[:6]) + '"', k + 1) if len(ws) >= 2 else []
    stage = "phrase" if rows else "or"
    if not rows:
        f = keep(ws)[:8]
        rows = fts(" OR ".join(f'"{w}"' for w in f), k + 1) if f else []
    truncated = len(rows) > k
    return stage, [h for h in (info(r[0]) for r in rows[:k]) if h], truncated


def lookup(text):
    ws = words(text); nw = len(ws)
    if nw < 2: return {"status": "too_short", "cand_pids": set(), "candidates": []}
    stage, hits, truncated = retrieve(ws)
    if not hits: return {"status": "none", "cand_pids": set(), "candidates": []}
    top = hits[0]
    kw = keep(ws)[:8]
    tw = set(words(top[5]))
    overlap = sum(w in tw for w in kw) / max(len(kw), 1)
    poets = {h[1] for h in hits}
    if stage == "phrase":
        # A phrase with more than k occurrences is too common to certify as belonging to a single poet:
        # the unseen occurrences may belong to someone else (found on real data: «و روشن دل و»).
        st = "ambiguous" if len(poets) > 1 else ("answer" if nw >= 4 and not truncated else "uncertain")
    else:
        agree = sum(h[1] == top[1] for h in hits[:3])
        st = "answer" if (overlap >= 0.8 and len(kw) >= 4 and agree >= 2) else "uncertain"
    return {"status": st, "poet": top[2], "pid": top[1], "verse": top[5], "overlap": round(overlap, 2),
            "candidates": list(dict.fromkeys(h[2] for h in hits)), "cand_pids": poets}



TRIGGERS = ("از کیست", "سروده کیست", "کدام شاعر", "شاعرش", "کی گفته", "مال کیست")


def attribution(question: str):
    """Deterministic 'who wrote this verse?' answer, or None if this is not an attribution request."""
    if not any(t in question for t in TRIGGERS):
        return None
    q = question
    for t in TRIGGERS:
        q = q.replace(t, " ")
    r = lookup(q)
    if r["status"] == "answer":
        return f"«{r['verse']}»\n— {r['poet']}"
    if r["status"] in ("ambiguous", "uncertain") and r["candidates"]:
        return "مطمئن نیستم؛ احتمالاً از: " + "، ".join(r["candidates"][:3])
    return "این بیت را در مجموعه‌ی شعرم پیدا نکردم."
