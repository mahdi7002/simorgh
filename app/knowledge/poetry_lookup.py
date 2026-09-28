import sqlite3, random, re
import os
DB = os.environ.get("SIMORGH_POETRY_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "poetry", "persian_poetry.db"))
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
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
        return db.execute("SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? ORDER BY bm25(verses_fts) LIMIT ?", (q, k)).fetchall()
    except Exception:
        return db.execute("SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? LIMIT ?", (q, k)).fetchall()
def info(rid):
    return db.execute("SELECT v.id,v.poet_id,p.name,v.poem_id,v.bait_number,v.text FROM verses v JOIN poets p ON p.id=v.poet_id WHERE v.id=?", (rid,)).fetchone()
def retrieve(ws, k=8):
    rows = fts('"' + " ".join(ws[:6]) + '"', k) if len(ws) >= 2 else []
    stage = "phrase" if rows else "or"
    if not rows:
        f = keep(ws)[:8]
        rows = fts(" OR ".join(f'"{w}"' for w in f), k) if f else []
    return stage, [h for h in (info(r[0]) for r in rows) if h]

def lookup(text):
    ws = words(text); nw = len(ws)
    if nw < 2: return {"status": "too_short", "cand_pids": set(), "candidates": []}
    stage, hits = retrieve(ws)
    if not hits: return {"status": "none", "cand_pids": set(), "candidates": []}
    top = hits[0]
    kw = keep(ws)[:8]
    tw = set(words(top[5]))
    overlap = sum(w in tw for w in kw) / max(len(kw), 1)
    poets = {h[1] for h in hits}
    if stage == "phrase":
        st = "ambiguous" if len(poets) > 1 else ("answer" if nw >= 4 else "uncertain")
    else:
        agree = sum(h[1] == top[1] for h in hits[:3])
        st = "answer" if (overlap >= 0.8 and len(kw) >= 4 and agree >= 2) else "uncertain"
    return {"status": st, "poet": top[2], "pid": top[1], "verse": top[5], "overlap": round(overlap, 2),
            "candidates": list(dict.fromkeys(h[2] for h in hits)), "cand_pids": poets}

