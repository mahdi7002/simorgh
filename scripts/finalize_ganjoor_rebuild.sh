#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
DB="data/simorgh_full.db"
SOURCE_DIR="rebuild_staging/ganjoor-data"
STAGING="rebuild_staging/ganjoor_simorgh_full.db"
REF="a64968e78425b2e8c7904fbdf5289fba8251a757"

usage() {
  cat <<'EOF'
Usage:
  scripts/finalize_ganjoor_rebuild.sh verify
  scripts/finalize_ganjoor_rebuild.sh apply

verify  rebuilds a complete staging corpus and compares it to the pinned
        Ganjoor snapshot. It never changes the canonical database.
apply   runs the same verification first, then atomically replaces the
        canonical database and leaves a timestamped pre-apply backup.
EOF
}

case "${1:-verify}" in
  verify|apply) ;;
  *) usage; exit 2 ;;
esac

rm -f "${STAGING}" "${STAGING}.json"
mkdir -p rebuild_staging

python3 scripts/rebuild_poems_from_ganjoor.py \
  --db "${DB}" \
  --output "${STAGING}" \
  --source-dir "${SOURCE_DIR}" \
  --ref "${REF}" \
  --max-chars 0

python3 scripts/verify_ganjoor_rebuild.py \
  --db "${STAGING}" \
  --source-dir "${SOURCE_DIR}" \
  --ref "${REF}"

python3 - "${STAGING}" <<'PY'
import sqlite3
import sys
from pathlib import Path

p = Path(sys.argv[1])
with sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True) as conn:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
    fts = conn.execute(
        "SELECT COUNT(*) FROM poems_fts"
    ).fetchone()[0]
print(f"STAGING integrity={integrity} poems={count} fts_rows={fts}")
if integrity != "ok" or count != 135319 or fts != 135319:
    raise SystemExit(1)
PY

if [[ "${1:-verify}" == "apply" ]]; then
  python3 scripts/rebuild_poems_from_ganjoor.py \
    --db "${DB}" \
    --output "${STAGING}" \
    --source-dir "${SOURCE_DIR}" \
    --ref "${REF}" \
    --max-chars 0 \
    --apply

  python3 - "${DB}" <<'PY'
import sqlite3
import sys
from pathlib import Path

p = Path(sys.argv[1])
with sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True) as conn:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
    fts = conn.execute("SELECT COUNT(*) FROM poems_fts").fetchone()[0]
print(f"CANONICAL integrity={integrity} poems={count} fts_rows={fts}")
if integrity != "ok" or count != 135319 or fts != 135319:
    raise SystemExit(1)
PY
fi
