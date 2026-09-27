#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${REPO}/.venv/bin/python"
LAYER="${REPO}/scripts/simorgh_knowledge_layer_v2.py"

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: ${PYTHON} not found"
  exit 2
fi

if [[ ! -f "${LAYER}" ]]; then
  echo "ERROR: ${LAYER} not found"
  exit 2
fi

"${PYTHON}" -m py_compile "${LAYER}"

TMP_DATA="$(mktemp -d -t simorgh-knowledge-smoke-XXXXXX)"
trap 'rm -rf "${TMP_DATA}"' EXIT

TMP_KNOWLEDGE_DB="${TMP_DATA}/knowledge.db"
TMP_SCHEMA="${TMP_DATA}/SIMORGH_KNOWLEDGE_SCHEMA_v2.sql"
cp "${REPO}/SIMORGH_KNOWLEDGE_SCHEMA_v2.sql" "${TMP_SCHEMA}"

"${PYTHON}" - <<PY
from pathlib import Path
import importlib.util

repo = Path(${REPO@Q})
tmp = Path(${TMP_DATA@Q})
spec = importlib.util.spec_from_file_location(
    "simorgh_knowledge_layer_v2", repo / "scripts/simorgh_knowledge_layer_v2.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.KNOWLEDGE_DB = tmp / "knowledge.db"
mod.SCHEMA_PATH = tmp / "SIMORGH_KNOWLEDGE_SCHEMA_v2.sql"
mod.DATA = tmp / "empty-data"
mod.DATA.mkdir()
mod.init_knowledge_db()
mod.seed_initial_facts()

cases = [
    ("رستم فرزند چه کسی است؟", "TRUE"),
    ("چه کسی مادر رستم است؟", "TRUE"),
    ("سیمرغ پدر رستم است؟", "UNKNOWN"),
    ("زال مادر رستم است؟", "UNKNOWN"),
    ("سیمرغ پسر زال است؟", "UNKNOWN"),
]

with mod.connect_knowledge() as db:
    for q, expected in cases:
        parsed = mod.parse_relation_question(db, q)
        assert parsed is not None, (q, "PARSE_FAILED")
        got = mod.query_relation(parsed)["state"]
        assert got == expected, (q, got, expected, parsed)

print("SMOKE_OK")
PY
