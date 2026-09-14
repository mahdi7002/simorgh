"""Strict test bootstrap.

The project root is added explicitly, and Starlette's current TestClient
compatibility layer is activated before test modules import it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import httpx2
except ImportError as exc:  # pragma: no cover - CI installs requirements-dev
    raise RuntimeError("httpx2 is required for the strict test suite") from exc

httpx2.alias_httpx()
