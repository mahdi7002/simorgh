#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "======== SIMORGH FULL SCAN ========"
echo "ROOT=$PWD DATE=$(date -Iseconds)"
echo "--- git ---"; git rev-parse --short HEAD; git status -sb
echo "--- python ---"; python3 --version
echo "--- disk/mem ---"; df -h . | head -3; free -h 2>/dev/null | head -2 || true
echo "--- hardcode ---"; grep -rn '/home/mahdi' --include='*.py' . 2>/dev/null | grep -v __pycache__ || echo none
echo "--- db ---"
python3 - <<'PY'
import sqlite3
from pathlib import Path
for p in Path('.').rglob('*.db'):
    if any(x in str(p) for x in ('.venv','.git')): continue
    try:
        c=sqlite3.connect(f'file:{p}?mode=ro', uri=True)
        print(p, c.execute('PRAGMA integrity_check').fetchone()[0], p.stat().st_size)
        c.close()
    except Exception as e:
        print(p, e)
PY
echo "--- main + provenance ---"
python3 - <<'PY'
import main
from core.memory import MemoryEngine
print('routes', len(main.app.routes))
m=MemoryEngine(); m.store_with_provenance('scan probe','full_scan',1.0,'KNOWN')
print(m.search_with_provenance('scan probe'))
PY
echo "--- pytest ---"; PYTHONPATH=. pytest -q
echo "--- demo ---"; python3 demo/simorgh_minimal.py --test
echo "======== DONE ========"
