"""Central, portable filesystem paths for SIMORGH.

All runtime paths are rooted at the repository by default and can be overridden
with environment variables for local/system deployments.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("SIMORGH_DATA_DIR", ROOT / "data")).expanduser().resolve()
MEMORY_DIR = Path(os.environ.get("SIMORGH_MEMORY_DIR", ROOT / "memory")).expanduser().resolve()
AUDIO_OUT_DIR = Path(os.environ.get("SIMORGH_AUDIO_OUT_DIR", ROOT / "audio_out")).expanduser().resolve()
IMPORTS_DIR = Path(os.environ.get("SIMORGH_IMPORTS_DIR", ROOT / "imports")).expanduser().resolve()
TRANSCRIPTS_DIR = Path(os.environ.get("SIMORGH_TRANSCRIPTS_DIR", ROOT / "transcripts")).expanduser().resolve()
LOG_DIR = Path(os.environ.get("SIMORGH_LOG_DIR", ROOT / "logs")).expanduser().resolve()
SNAPSHOT_DIR = Path(os.environ.get("SIMORGH_SNAPSHOT_DIR", DATA_DIR / "snapshots")).expanduser().resolve()
PROPOSAL_DIR = Path(os.environ.get("SIMORGH_PROPOSAL_DIR", DATA_DIR / "reflection_proposals")).expanduser().resolve()
DASHBOARD_HTML = Path(os.environ.get("SIMORGH_DASHBOARD_HTML", ROOT / "dashboard" / "index.html")).expanduser().resolve()

QURAN_DB = Path(os.environ.get("SIMORGH_QURAN_DB", DATA_DIR / "grid" / "quran.db")).expanduser().resolve()
POETRY_DB = Path(os.environ.get("SIMORGH_POETRY_DB", DATA_DIR / "simorgh_full.db")).expanduser().resolve()
APP_DB = Path(os.environ.get("SIMORGH_APP_DB", DATA_DIR / "simorgh.db")).expanduser().resolve()
BOOKS_DB = Path(os.environ.get("SIMORGH_BOOKS_DB", DATA_DIR / "books.db")).expanduser().resolve()
LIBRARY_DB = Path(os.environ.get("SIMORGH_LIBRARY_DB", DATA_DIR / "library_catalog.db")).expanduser().resolve()
MEMORY_DB = Path(os.environ.get("SIMORGH_MEMORY_DB", MEMORY_DIR / "short_term.db")).expanduser().resolve()
JOURNAL_DB = Path(os.environ.get("SIMORGH_JOURNAL_DB", MEMORY_DIR / "journal.db")).expanduser().resolve()
ACTIVITY_DB = Path(os.environ.get("SIMORGH_ACTIVITY_DB", DATA_DIR / "activity.db")).expanduser().resolve()

PIPER_BIN = Path(os.environ.get("SIMORGH_PIPER_BIN", ROOT / "bin" / "piper")).expanduser()
PIPER_MODEL = Path(os.environ.get("SIMORGH_PIPER_MODEL", ROOT / "models" / "piper" / "fa_IR-gyro-medium.onnx")).expanduser()
SCAN_ROOT = Path(os.environ.get("SIMORGH_SCAN_ROOT", ROOT / "library" / "incoming")).expanduser().resolve()

def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, MEMORY_DIR, AUDIO_OUT_DIR, IMPORTS_DIR, TRANSCRIPTS_DIR, LOG_DIR, SNAPSHOT_DIR, PROPOSAL_DIR):
        path.mkdir(parents=True, exist_ok=True)

ensure_runtime_dirs()
