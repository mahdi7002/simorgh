#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    PYTHON="${PYTHON_FALLBACK:-python3}"
fi

cd "$ROOT"

bash -n scripts/simorgh-run.sh
bash -n scripts/install-mother-service.sh
"$PYTHON" -m compileall -q core/mother
"$PYTHON" -m pytest -q tests/test_mother_*.py

printf 'MOTHER_SMOKE_PASS\n'
