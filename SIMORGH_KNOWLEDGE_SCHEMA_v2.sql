-- SIMORGH Knowledge Sovereignty Layer v2
-- KNOWN != INFERRED
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS relation_types (
    relation_key TEXT PRIMARY KEY,
    label_fa TEXT NOT NULL,
    inverse_key TEXT,
    broader_key TEXT,
    symmetric INTEGER NOT NULL DEFAULT 0,
    description TEXT
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    entity_type TEXT,
    gender TEXT,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    provenance_note TEXT
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias TEXT PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    relation_id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES entities(entity_id),
    relation_key TEXT NOT NULL REFERENCES relation_types(relation_key),
    object_id INTEGER NOT NULL REFERENCES entities(entity_id),
    status TEXT NOT NULL,
    polarity TEXT NOT NULL DEFAULT 'ASSERTED'
        CHECK (polarity IN ('ASSERTED','NEGATED')),
    evidence_grade TEXT,
    extraction_method TEXT NOT NULL,
    created_by TEXT NOT NULL,
    UNIQUE(subject_id, relation_key, object_id, polarity)
);

CREATE TABLE IF NOT EXISTS relation_evidence (
    evidence_id INTEGER PRIMARY KEY,
    relation_id INTEGER NOT NULL REFERENCES knowledge_relations(relation_id) ON DELETE CASCADE,
    source_db TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_column TEXT,
    source_rowid INTEGER,
    source_locator TEXT,
    source_doc TEXT,
    source_category TEXT,
    evidence_text TEXT NOT NULL,
    evidence_hash TEXT,
    evidence_grade TEXT,
    extraction_method TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS relation_candidates (
    candidate_id INTEGER PRIMARY KEY,
    relation_hint TEXT NOT NULL,
    trigger TEXT NOT NULL,
    source_db TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_column TEXT,
    source_rowid INTEGER,
    source_locator TEXT,
    source_doc TEXT,
    snippet TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNREVIEWED'
        CHECK (status IN ('UNREVIEWED','REVIEWED','ACCEPTED','REJECTED')),
    UNIQUE(relation_hint, source_db, source_table, source_column, source_rowid, source_locator, trigger)
);

CREATE TABLE IF NOT EXISTS audit_runs (
    run_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    scanned_databases INTEGER NOT NULL DEFAULT 0,
    scanned_tables INTEGER NOT NULL DEFAULT 0,
    scanned_rows INTEGER NOT NULL DEFAULT 0,
    scanned_text_cells INTEGER NOT NULL DEFAULT 0,
    relation_candidates INTEGER NOT NULL DEFAULT 0,
    issues_found INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_issues (
    issue_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES audit_runs(run_id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    source_db TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_column TEXT,
    source_rowid INTEGER,
    source_locator TEXT,
    source_doc TEXT,
    details TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_relation_subject ON knowledge_relations(subject_id, relation_key);
CREATE INDEX IF NOT EXISTS idx_relation_object  ON knowledge_relations(object_id, relation_key);
CREATE INDEX IF NOT EXISTS idx_relation_type    ON knowledge_relations(relation_key);
CREATE INDEX IF NOT EXISTS idx_evidence_relation ON relation_evidence(relation_id);
CREATE INDEX IF NOT EXISTS idx_candidates_hint ON relation_candidates(relation_hint);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON relation_candidates(status);
CREATE INDEX IF NOT EXISTS idx_audit_source ON audit_issues(source_db, source_table, source_rowid, source_locator);

CREATE VIEW IF NOT EXISTS v_relation_facts AS
SELECT r.relation_id, s.canonical_name AS subject, r.relation_key,
       rt.label_fa AS relation_label, o.canonical_name AS object,
       r.status, r.polarity, r.evidence_grade, r.extraction_method, r.created_by
FROM knowledge_relations r
JOIN entities s ON s.entity_id=r.subject_id
JOIN entities o ON o.entity_id=r.object_id
JOIN relation_types rt ON rt.relation_key=r.relation_key;

CREATE VIEW IF NOT EXISTS v_relation_evidence AS
SELECT f.relation_id, f.subject, f.relation_key, f.relation_label, f.object,
       f.status, f.polarity, e.source_db, e.source_table, e.source_column,
       e.source_rowid, e.source_locator, e.source_doc, e.source_category,
       e.evidence_text, e.evidence_grade, e.extraction_method
FROM v_relation_facts f
JOIN relation_evidence e ON e.relation_id=f.relation_id;

INSERT OR IGNORE INTO relation_types
(relation_key,label_fa,inverse_key,broader_key,symmetric,description) VALUES
('parent_of','والدِ','child_of',NULL,0,'والد عمومی'),
('child_of','فرزندِ','parent_of',NULL,0,'فرزند عمومی'),
('father_of','پدرِ','child_of','parent_of',0,'رابطه پدری خاص'),
('mother_of','مادرِ','child_of','parent_of',0,'رابطه مادری خاص'),
('son_of','پسرِ','parent_of','child_of',0,'فرزند مذکر'),
('daughter_of','دخترِ','parent_of','child_of',0,'فرزند مؤنث'),
('sibling_of','خواهر/برادرِ','sibling_of',NULL,1,'خواهر/برادری'),
('spouse_of','همسرِ','spouse_of',NULL,1,'همسری'),
('raised','پرورش‌داد','raised_by',NULL,0,'پرورش'),
('raised_by','تحت پرورشِ','raised',NULL,0,'پرورش از منظر مفعول'),
('helped','یاری‌کرد','helped_by',NULL,0,'یاری'),
('helped_by','از سوی او یاری‌شده','helped',NULL,0,'یاری معکوس'),
('advised','راهنمایی‌کرد','advised_by',NULL,0,'راهنمایی'),
('advised_by','از سوی او راهنمایی‌شده','advised',NULL,0,'راهنمایی معکوس'),
('mentor_of','استاد/مرشدِ','mentored_by',NULL,0,'استاد/مرشد'),
('mentored_by','شاگرد/تحت آموزشِ','mentor_of',NULL,0,'شاگردی'),
('friend_of','دوستِ','friend_of',NULL,1,'دوستی'),
('enemy_of','دشمنِ','enemy_of',NULL,1,'دشمنی'),
('born_in','زاده‌شده در','birthplace_of',NULL,0,'محل تولد'),
('birthplace_of','زادگاهِ','born_in',NULL,0,'زادگاه'),
('died_in','درگذشته در','deathplace_of',NULL,0,'محل مرگ'),
('deathplace_of','محل درگذشتِ','died_in',NULL,0,'محل درگذشت'),
('authored','نوشته/سروده','authored_by',NULL,0,'پدیدآورندگی'),
('authored_by','نوشته/سروده‌شده توسط','authored',NULL,0,'پدیدآورندگی معکوس'),
('located_in','واقع در','contains',NULL,0,'رابطه مکانی'),
('contains','شامل','located_in',NULL,0,'رابطه مکانی معکوس');
