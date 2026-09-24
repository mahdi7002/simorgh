"""
core/paths.py — مسیرهای مرکزی پروژه
=====================================
پیش از این، هر فایل مستقیماً به /home/mahdi/... اشاره می‌کرد — یعنی
پروژه فقط روی دستگاه شخصی سازنده اجرا می‌شد. این ماژول همه‌ی مسیرها
را یک‌جا، نسبت به ریشه‌ی خودِ ریپو تعریف می‌کند، با امکان override از
طریق متغیر محیطی برای استقرارهای دیگر.
"""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = Path(os.environ.get("SIMORGH_DATA_DIR", str(ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

QURAN_DB = Path(os.environ.get("SIMORGH_QURAN_DB", str(DATA_DIR / "quran.db")))
POETRY_DB = Path(os.environ.get("SIMORGH_POETRY_DB", str(DATA_DIR / "simorgh.db")))
ACTIVITY_DB = Path(os.environ.get("SIMORGH_ACTIVITY_DB", str(DATA_DIR / "activity.db")))
BOOKS_DB = Path(os.environ.get("SIMORGH_BOOKS_DB", str(DATA_DIR / "books.db")))

DASHBOARD_HTML = Path(os.environ.get("SIMORGH_DASHBOARD_HTML", str(ROOT / "dashboard" / "index.html")))

_piper_env = os.environ.get("SIMORGH_PIPER_BIN")
PIPER_BIN = _piper_env or shutil.which("piper") or str(ROOT / "bin" / "piper")

_default_scan_root = str(ROOT / "library" / "incoming")
SCAN_ROOTS = [os.environ.get("SIMORGH_SCAN_ROOT", _default_scan_root)]
