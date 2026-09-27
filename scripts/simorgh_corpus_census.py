#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path("data")
OUTPUT = ROOT / "corpus_census.json"
EXCLUDE = (ROOT / "simorgh_knowledge.db").resolve()

TEXT_HINTS = (
    "title", "name", "source", "author", "category", "chapter",
    "section", "page", "doc", "document", "book", "text",
)

TEXT_TYPES = (
    "TEXT", "CHAR", "CLOB", "VARCHAR", "NVARCHAR", "NTEXT"
)


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_text(decl: str) -> bool:
    t = (decl or "").upper()
    return any(x in t for x in TEXT_TYPES)


def inspect_table(conn: sqlite3.Connection, table: str) -> dict:
    qt = qident(table)

    columns = []
    text_columns = []
    hint_columns = []

    for row in conn.execute(f"PRAGMA table_info({qt})"):
        cid, name, decl, notnull, default_value, pk = row
        columns.append({
            "cid": cid,
            "name": name,
            "declared_type": decl,
            "not_null": bool(notnull),
            "primary_key": bool(pk),
        })

        if is_text(decl):
            text_columns.append(name)

        low = name.lower()
        if any(h in low for h in TEXT_HINTS):
            hint_columns.append(name)

    row_count = conn.execute(
        f"SELECT COUNT(*) FROM {qt}"
    ).fetchone()[0]

    sql_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()

    sql = sql_row[0] if sql_row else None
    is_fts = bool(
        sql and
        "VIRTUAL TABLE" in sql.upper() and
        "FTS" in sql.upper()
    )

    samples = {}

    for col in hint_columns[:10]:
        try:
            rows = conn.execute(
                f"""
                SELECT DISTINCT {qident(col)}
                FROM {qt}
                WHERE {qident(col)} IS NOT NULL
                  AND TRIM(CAST({qident(col)} AS TEXT)) <> ''
                LIMIT 20
                """
            ).fetchall()
            samples[col] = [str(r[0])[:300] for r in rows]
        except sqlite3.Error as e:
            samples[col] = {"error": str(e)}

    return {
        "table": table,
        "row_count": row_count,
        "columns": columns,
        "text_columns": text_columns,
        "hint_columns": hint_columns,
        "fts": is_fts,
        "sql": sql,
        "samples": samples,
    }


def inspect_db(path: Path) -> dict:
    resolved = path.resolve()

    result = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "integrity_check": None,
        "tables": [],
        "errors": [],
    }

    uri = f"file:{resolved}?mode=ro"

    try:
        conn = sqlite3.connect(uri, uri=True)

        try:
            result["integrity_check"] = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        except sqlite3.Error as e:
            result["errors"].append(f"integrity_check: {e}")

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table,) in tables:
            try:
                result["tables"].append(
                    inspect_table(conn, table)
                )
            except sqlite3.Error as e:
                result["errors"].append(
                    f"{table}: {e}"
                )

        conn.close()

    except sqlite3.Error as e:
        result["errors"].append(str(e))

    return result


def main() -> int:
    databases = []

    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        databases.extend(ROOT.rglob(pattern))

    unique = []
    seen = set()

    for path in sorted(databases):
        resolved = path.resolve()

        if resolved == EXCLUDE:
            continue

        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)

    report = {
        "schema_version": 1,
        "root": str(ROOT.resolve()),
        "databases_found": len(unique),
        "databases": [],
    }

    for path in unique:
        print(f"[SCAN DB] {path}", flush=True)
        report["databases"].append(
            inspect_db(path)
        )

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tables = sum(
        len(db["tables"])
        for db in report["databases"]
    )

    rows = sum(
        table["row_count"]
        for db in report["databases"]
        for table in db["tables"]
    )

    print()
    print("=== SIMORGH CORPUS CENSUS ===")
    print(f"DATABASES : {len(unique)}")
    print(f"TABLES    : {tables}")
    print(f"ROWS      : {rows:,}")
    print(f"REPORT    : {OUTPUT}")

    print()
    for db in report["databases"]:
        print(f"[DB] {db['path']}")

        for table in db["tables"]:
            fts = " FTS" if table["fts"] else ""
            text_cols = ",".join(table["text_columns"]) or "-"
            print(
                f"  {table['table']}"
                f" | rows={table['row_count']:,}"
                f" | text={text_cols}"
                f"{fts}"
            )

        if db["errors"]:
            for error in db["errors"]:
                print(f"  [ERROR] {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
