#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KNOWLEDGE_DB = DATA / "simorgh_knowledge.db"
SCHEMA_PATH = ROOT / "SIMORGH_KNOWLEDGE_SCHEMA_v2.sql"
REPORT_PATH = ROOT / "knowledge_audit_report.json"
SELF_DOCS = {"معرفی_سیمرغ", "معماری_سیمرغ"}

RELATION_TRIGGERS = {
    "father":["پدر"], "mother":["مادر"], "parent":["والد","والدین"],
    "child":["فرزند","پسر","دختر"], "sibling":["برادر","خواهر"],
    "spouse":["همسر","شوهر"], "raised":["بزرگ کرد","پرورش داد","پرورش یافت","بزرگ شد"],
    "help":["یاری","کمک","نجات","دستگیری"], "advised":["راهنمایی","راهنما","پند داد","نصیحت"],
    "mentor":["استاد","شاگرد","آموزگار"], "friend":["دوست"], "enemy":["دشمن"],
    "birth":["زاده شد","به دنیا آمد","زاده"], "death":["درگذشت","وفات یافت","فوت کرد","کشته شد"],
    "authorship":["نویسنده","سروده","سراینده","نوشت","تألیف","آفرید"],
    "location":["واقع در","قرار دارد","ساکن"]}

ISSUE_PATTERNS = {"WEB_METADATA":["ویکی‌نبشته","فهرست آثار","دانلود کنید","نوشتارهای تازه","کتابخانه‌ای آزاد"],
                  "HTML":["<html","<div","</","<body","<p>"]}
ENTITY_SEEDS = {
    "زال":{"aliases":["زال","دستان"],"type":"PERSON"},
    "رستم":{"aliases":["رستم","تهمتن"],"type":"PERSON"},
    "سام":{"aliases":["سام"],"type":"PERSON"},
    "رودابه":{"aliases":["رودابه","روداب"],"type":"PERSON"},
    "سیمرغ":{"aliases":["سیمرغ"],"type":"MYTHIC_ENTITY"}}

BINARY_EXACT_PATTERNS = [
    ("father_of",r"^(?P<x>.+?) پدر (?P<y>.+?) است$"),
    ("mother_of",r"^(?P<x>.+?) مادر (?P<y>.+?) است$"),
    ("parent_of",r"^(?P<x>.+?) (?:والد|والدین) (?P<y>.+?) است$"),
    ("son_of",r"^(?P<x>.+?) پسر (?P<y>.+?) است$"),
    ("daughter_of",r"^(?P<x>.+?) دختر (?P<y>.+?) است$"),
    ("sibling_of",r"^(?P<x>.+?) (?:برادر|خواهر) (?P<y>.+?) است$"),
    ("spouse_of",r"^(?P<x>.+?) همسر (?P<y>.+?) است$"),
    ("raised",r"^(?P<x>.+?) (?P<y>.+?) را (?:بزرگ|پرورش) داد$"),
    ("helped",r"^(?P<x>.+?) به (?P<y>.+?) کمک کرد$"),
    ("advised",r"^(?P<x>.+?) به (?P<y>.+?) (?:پند|نصیحت|راهنمایی) داد$"),
    ("friend_of",r"^(?P<x>.+?) دوست (?P<y>.+?) بود$"),
    ("enemy_of",r"^(?P<x>.+?) دشمن (?P<y>.+?) بود$"),
]

QUESTION_PATTERNS = [
    ("father_of","SUBJECT",r"^(?P<x>.+?) پدر چه کسی است$"),
    ("mother_of","SUBJECT",r"^(?P<x>.+?) مادر چه کسی است$"),
    ("parent_of","SUBJECT",r"^(?P<x>.+?) (?:والد|والدین) چه کسی است$"),
    ("father_of","OBJECT",r"^چه کسی پدر (?P<y>.+?) است$"),
    ("mother_of","OBJECT",r"^چه کسی مادر (?P<y>.+?) است$"),
    ("parent_of","OBJECT",r"^چه کسی (?:والد|والدین) (?P<y>.+?) است$"),
    ("parent_of","OBJECT",r"^(?P<x>.+?) (?:پسر|فرزند) چه کسی است$"),
    ("sibling_of","SUBJECT",r"^(?P<x>.+?) (?:خواهر|برادر) چه کسی است$"),
    ("spouse_of","SUBJECT",r"^(?P<x>.+?) همسر چه کسی است$"),
    ("raised_by","OBJECT",r"^(?P<y>.+?) تحت (?:پرورش|سرپرستی) چه کسی بود$"),
    ("helped","SUBJECT",r"^(?P<x>.+?) به چه کسی کمک کرد$"),
    ("advised","SUBJECT",r"^(?P<x>.+?) به چه کسی (?:پند|نصیحت|راهنمایی) داد$"),
    ("friend_of","SUBJECT",r"^(?P<x>.+?) دوست چه کسی بود$"),
    ("enemy_of","SUBJECT",r"^(?P<x>.+?) دشمن چه کسی بود$"),
    ("born_in","SUBJECT",r"^(?P<x>.+?) کجا زاده شد$"),
    ("died_in","SUBJECT",r"^(?P<x>.+?) کجا درگذشت$"),
]

def utc_now(): return datetime.now(timezone.utc).isoformat()

def normalize(text):
    text = text or ""
    for a,b in {"ھ":"ه","ۀ":"ه","ي":"ی","ى":"ی","ك":"ک","\u200c":" ","\u200d":" ","\ufeff":" "}.items(): text=text.replace(a,b)
    text=re.sub(r"[ـ]+","",text)
    return re.sub(r"\s+"," ",text).strip()

def normalize_question(text): return normalize(text).rstrip("؟?!").strip()

def db_paths():
    out=[]
    for p in sorted(DATA.rglob("*")):
        if p.suffix.lower() not in {".db",".sqlite",".sqlite3"}: continue
        if p.resolve() == KNOWLEDGE_DB.resolve(): continue
        out.append(p)
    return out

def quote_ident(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",value): raise ValueError(value)
    return f'"{value}"'

def connect_knowledge():
    KNOWLEDGE_DB.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(KNOWLEDGE_DB); con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON"); return con

def init_knowledge_db():
    with connect_knowledge() as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        for canonical,info in ENTITY_SEEDS.items():
            db.execute("INSERT OR IGNORE INTO entities(canonical_name,entity_type,status,provenance_note) VALUES(?,?, 'CANDIDATE','seeded_for_query_prototype')",(canonical,info["type"]))
            eid=db.execute("SELECT entity_id FROM entities WHERE canonical_name=?",(canonical,)).fetchone()[0]
            for alias in info["aliases"]: db.execute("INSERT OR IGNORE INTO entity_aliases(alias,entity_id) VALUES(?,?)",(alias,eid))
        db.commit()

def table_names(db):
    rows=db.execute("SELECT name,type,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    virtuals={r[0] for r in rows if r[1]=='table' and 'USING FTS' in (r[2] or '').upper()}
    suffixes=("_data","_idx","_content","_docsize","_config")
    return [r[0] for r in rows if r[1] in {'table','virtual table'} and not any(r[0]==f'{v}{s}' for v in virtuals for s in suffixes)]

def candidate_text_columns(db,table):
    out=[]
    for r in db.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall():
        name,decl=r[1],(r[2] or '').upper()
        if name.lower()=='id': continue
        if decl in {'TEXT','','VARCHAR','CHAR','CLOB'}: out.append(name)
    return out

def has_rowid(db,table):
    row=db.execute("SELECT sql FROM sqlite_master WHERE name=?",(table,)).fetchone()
    return 'WITHOUT ROWID' not in ((row[0] or '').upper() if row else '')

def source_locator(record,rowid):
    if isinstance(rowid,int): return rowid,f'rowid:{rowid}'
    parts=[f'{k}={v}' for k,v in record.items() if v is not None and (k.lower().endswith('id') or k.lower() in {'key','name'})]
    if parts: return None,'pk:'+'|'.join(parts)
    digest=hashlib.sha256(json.dumps(record,ensure_ascii=False,default=str,sort_keys=True).encode()).hexdigest()[:24]
    return None,f'hash:{digest}'

def display_doc_name(record):
    for key in ('doc_name','title','poet','category','name'):
        v=record.get(key)
        if isinstance(v,str) and v.strip(): return v.strip()
    return None

def evidence_window(text,start,end,radius=180): return normalize(text[max(0,start-radius):min(len(text),end+radius)])

def issue_scan(kdb,dbpath,table,column,rowid,locator,value,doc,run_id):
    raw=value; normalized=normalize(value); issues=[]
    if not raw.strip(): issues.append(('LOW','EMPTY_TEXT','Empty textual cell.'))
    if '\x00' in raw: issues.append(('HIGH','NUL_BYTE','NUL byte present.'))
    if '�' in raw: issues.append(('MEDIUM','REPLACEMENT_CHAR','Unicode replacement character present.'))
    if len(raw)>=100 and raw.count('ھ')>=5: issues.append(('MEDIUM','OCR_GLYPH_DENSITY',"Frequent OCR glyph 'ھ' detected."))
    if len(raw)>=100 and sum(raw.count(c) for c in ('ي','ك','ى','ۀ'))>=10: issues.append(('LOW','ORTHOGRAPHY_VARIANT','Arabic/Persian orthography variants detected.'))
    for typ,needles in ISSUE_PATTERNS.items():
        if any(n in normalized for n in needles): issues.append(('MEDIUM' if typ=='WEB_METADATA' else 'HIGH',typ,f'Pattern detected from {needles!r}.'))
    if doc in SELF_DOCS: issues.append(('HIGH','SYSTEM_DOC_IN_CORPUS','Known SIMORGH self-document is inside general corpus.'))
    for sev,typ,details in issues:
        kdb.execute("INSERT INTO audit_issues(run_id,severity,issue_type,source_db,source_table,source_column,source_rowid,source_locator,source_doc,details) VALUES(?,?,?,?,?,?,?,?,?,?)",(run_id,sev,typ,str(dbpath),table,column,rowid,locator,doc,details))
    return len(issues)


# Fast single-pass relation trigger matcher.
_RELATION_TRIGGER_TO_HINT = {}
for _hint, _triggers in RELATION_TRIGGERS.items():
    for _trigger in _triggers:
        _RELATION_TRIGGER_TO_HINT[_trigger] = _hint

_RELATION_TRIGGER_RE = re.compile(
    "|".join(
        re.escape(t)
        for t in sorted(
            _RELATION_TRIGGER_TO_HINT,
            key=len,
            reverse=True,
        )
    )
)

def relation_candidate_scan(
    kdb, dbpath, table, column, rowid, locator, value, doc
):
    text = normalize(value)
    if not text:
        return 0

    inserted = 0
    seen_hints = set()

    # Exactly one regex pass over the cell.
    for match in _RELATION_TRIGGER_RE.finditer(text):
        trigger = match.group(0)
        hint = _RELATION_TRIGGER_TO_HINT[trigger]

        # One candidate per relation family per cell.
        if hint in seen_hints:
            continue

        seen_hints.add(hint)

        before = kdb.total_changes

        kdb.execute(
            """
            INSERT OR IGNORE INTO relation_candidates
            (
                relation_hint,
                trigger,
                source_db,
                source_table,
                source_column,
                source_rowid,
                source_locator,
                source_doc,
                snippet,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNREVIEWED')
            """,
            (
                hint,
                trigger,
                str(dbpath),
                table,
                column,
                rowid,
                locator,
                doc,
                evidence_window(
                    text,
                    match.start(),
                    match.end(),
                ),
            ),
        )

        inserted += kdb.total_changes - before

    return inserted


def run_full_audit():
    init_knowledge_db(); started=utc_now()
    with connect_knowledge() as kdb:
        run_id=kdb.execute("INSERT INTO audit_runs(started_at) VALUES(?)",(started,)).lastrowid
        scanned_db=scanned_tables=scanned_rows=scanned_cells=candidates=issues=0
        for path in db_paths():
            scanned_db += 1
            try:
                with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
                    db.row_factory = sqlite3.Row
                    for table in table_names(db):
                        cols = candidate_text_columns(db, table)
                        if not cols:
                            continue
                        scanned_tables += 1
                        prefix = 'rowid, ' if has_rowid(db, table) else ''
                        query = f"SELECT {prefix}{', '.join(quote_ident(c) for c in cols)} FROM {quote_ident(table)}"
                        try:
                            cursor = db.execute(query)
                        except sqlite3.DatabaseError as exc:
                            kdb.execute("INSERT INTO audit_issues(run_id,severity,issue_type,source_db,source_table,details) VALUES(?,?,?,?,?,?)", (run_id, 'HIGH', 'TABLE_SCAN_ERROR', str(path), table, str(exc)))
                            issues += 1
                            continue
                        print(
                            f"[AUDIT TABLE] {path.name} :: {table} "
                            f":: text_columns={len(cols)}",
                            flush=True,
                        )

                        for row in cursor:
                            scanned_rows += 1

                            # Durable progress checkpoint.
                            # An interrupted long audit keeps the last checkpoint.
                            if scanned_rows % 5000 == 0:
                                kdb.execute(
                                    """
                                    UPDATE audit_runs
                                    SET scanned_databases=?,
                                        scanned_tables=?,
                                        scanned_rows=?,
                                        scanned_text_cells=?,
                                        relation_candidates=?,
                                        issues_found=?
                                    WHERE run_id=?
                                    """,
                                    (
                                        scanned_db,
                                        scanned_tables,
                                        scanned_rows,
                                        scanned_cells,
                                        candidates,
                                        issues,
                                        run_id,
                                    ),
                                )
                                kdb.commit()

                                print(
                                    f"[AUDIT] db={scanned_db} "
                                    f"tables={scanned_tables} "
                                    f"rows={scanned_rows} "
                                    f"cells={scanned_cells} "
                                    f"candidates={candidates} "
                                    f"issues={issues}",
                                    flush=True,
                                )

                            record = dict(row)
                            rid = record.pop('rowid', None)
                            rowid, locator = source_locator(record, rid)
                            doc = display_doc_name(record)
                            for column in cols:
                                value = record.get(column)
                                if not isinstance(value, str):
                                    continue
                                scanned_cells += 1
                                issues += issue_scan(kdb, path, table, column, rowid, locator, value, doc, run_id)
                                candidates += relation_candidate_scan(kdb, path, table, column, rowid, locator, value, doc)
            except sqlite3.DatabaseError as exc:
                kdb.execute("INSERT INTO audit_issues(run_id,severity,issue_type,source_db,source_table,details) VALUES(?,?,?,?,?,?)", (run_id, 'HIGH', 'DATABASE_SCAN_ERROR', str(path), '', str(exc)))
                issues += 1
        kdb.execute("UPDATE audit_runs SET finished_at=?,scanned_databases=?,scanned_tables=?,scanned_rows=?,scanned_text_cells=?,relation_candidates=?,issues_found=? WHERE run_id=?", (utc_now(), scanned_db, scanned_tables, scanned_rows, scanned_cells, candidates, issues, run_id))
        kdb.commit()
    result={'run_id':int(run_id),'knowledge_db':str(KNOWLEDGE_DB),'scanned_databases':scanned_db,'scanned_tables':scanned_tables,'scanned_rows':scanned_rows,'scanned_text_cells':scanned_cells,'relation_candidates':candidates,'issues_found':issues}
    REPORT_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); return result

def seed_initial_facts():
    seed=[('سام','parent_of','زال','data/simorgh_full.db','book_chunks_fts','chunk_text',2444,'سام همراه فرزندش دستان زال'),('زال','parent_of','رستم','data/simorgh_full.db','book_chunks_fts','chunk_text',2452,'یزدان را سپاس که فرزند من رستم یگانه است'),('رودابه','mother_of','رستم','data/simorgh_full.db','book_chunks_fts','chunk_text',2457,'رودابه مادر رستم')]
    with connect_knowledge() as db:
        def eid(n): return int(db.execute("SELECT entity_id FROM entities WHERE canonical_name=?",(n,)).fetchone()[0])
        for s,r,o,sdb,table,col,rid,e in seed:
            sid,oid=eid(s),eid(o)
            db.execute("INSERT OR IGNORE INTO knowledge_relations(subject_id,relation_key,object_id,status,polarity,evidence_grade,extraction_method,created_by) VALUES(?,?,?,'EXPLICIT_EVIDENCE','ASSERTED','A','EXPLICIT_TEXT','initial_manual_seed_from_audit')",(sid,r,oid))
            relid=db.execute("SELECT relation_id FROM knowledge_relations WHERE subject_id=? AND relation_key=? AND object_id=? AND polarity='ASSERTED'",(sid,r,oid)).fetchone()[0]
            db.execute("INSERT OR IGNORE INTO relation_evidence(relation_id,source_db,source_table,source_column,source_rowid,source_locator,evidence_text,evidence_hash,evidence_grade,extraction_method) VALUES(?,?,?,?,?,?,?,?, 'A','EXPLICIT_TEXT')",(relid,sdb,table,col,rid,f'rowid:{rid}',e,hashlib.sha256(e.encode()).hexdigest()))
        db.commit()

def resolve_entity(db,phrase):
    hits=[]
    for row in db.execute("SELECT a.alias,e.canonical_name FROM entity_aliases a JOIN entities e ON e.entity_id=a.entity_id"):
        alias,canonical=row['alias'],row['canonical_name']
        for m in re.finditer(rf'(?<!\w){re.escape(alias)}(?!\w)',phrase): hits.append((m.start(),-(len(alias)),canonical))
    return sorted(hits)[0][2] if hits else None

def parse_relation_question(db,question):
    q=normalize_question(question)
    # Exact checks FIRST: position determines subject/object.
    for relation,pattern in BINARY_EXACT_PATTERNS:
        m=re.match(pattern,q)
        if m:
            x,y=resolve_entity(db,normalize(m.group('x'))),resolve_entity(db,normalize(m.group('y')))
            if x and y: return {'subject':x,'relation':relation,'object':y,'direction':'EXACT','entities':[x,y]}
    for relation,direction,pattern in QUESTION_PATTERNS:
        m=re.match(pattern,q)
        if not m: continue
        key='x' if 'x' in m.groupdict() else 'y'; entity=resolve_entity(db,normalize(m.group(key)))
        if entity:
            return {'subject':entity if direction=='SUBJECT' else None,'relation':relation,'object':entity if direction=='OBJECT' else None,'direction':direction,'entities':[entity]}
    return None

def relation_family(db,relation):
    return [r['relation_key'] for r in db.execute("SELECT relation_key FROM relation_types WHERE relation_key=? OR broader_key=? ORDER BY CASE WHEN relation_key=? THEN 0 ELSE 1 END, relation_key",(relation,relation,relation))]

def exact_state(db,subject,relation,obj):
    rows=db.execute("SELECT polarity FROM v_relation_facts WHERE subject=? AND relation_key=? AND object=?",(subject,relation,obj)).fetchall()
    a=any(r['polarity']=='ASSERTED' for r in rows); n=any(r['polarity']=='NEGATED' for r in rows)
    if a and n: return 'CONFLICT'
    if a: return 'TRUE'
    if n: return 'FALSE'
    return 'UNKNOWN'

def query_relation(parsed):
    with connect_knowledge() as db:
        if parsed['direction']=='EXACT': return {'parsed':parsed,'state':exact_state(db,parsed['subject'],parsed['relation'],parsed['object']),'rows':[]}
        allowed=relation_family(db,parsed['relation']); ph=','.join('?' for _ in allowed)
        if parsed['direction']=='SUBJECT':
            rows=db.execute(f"SELECT subject,relation_key AS relation,object,status,polarity,evidence_grade FROM v_relation_facts WHERE subject=? AND relation_key IN ({ph}) AND polarity='ASSERTED' ORDER BY relation_key,relation_id",[parsed['subject'],*allowed]).fetchall()
        else:
            rows=db.execute(f"SELECT subject,relation_key AS relation,object,status,polarity,evidence_grade FROM v_relation_facts WHERE object=? AND relation_key IN ({ph}) AND polarity='ASSERTED' ORDER BY relation_key,relation_id",[parsed['object'],*allowed]).fetchall()
        return {'parsed':parsed,'state':'TRUE' if rows else 'UNKNOWN','rows':[dict(r) for r in rows]}

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('init','audit','seed','summary','paths'): sub.add_parser(name)
    q=sub.add_parser('query'); q.add_argument('question')
    a=p.parse_args()
    if a.cmd=='init': init_knowledge_db(); print(f'initialized: {KNOWLEDGE_DB}')
    elif a.cmd=='audit': print(json.dumps(run_full_audit(),ensure_ascii=False,indent=2))
    elif a.cmd=='seed': init_knowledge_db(); seed_initial_facts(); print('seeded')
    elif a.cmd=='paths': print('\n'.join(map(str,db_paths())))
    elif a.cmd=='summary':
        init_knowledge_db()
        with connect_knowledge() as db:
            row=db.execute('SELECT * FROM audit_runs ORDER BY run_id DESC LIMIT 1').fetchone(); print(json.dumps(dict(row) if row else {},ensure_ascii=False,indent=2))
    elif a.cmd=='query':
        init_knowledge_db()
        with connect_knowledge() as db: parsed=parse_relation_question(db,a.question)
        if parsed is None: print(json.dumps({'question':a.question,'state':'PARSE_FAILED'},ensure_ascii=False,indent=2)); return 2
        print(json.dumps({'question':a.question,**query_relation(parsed)},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
