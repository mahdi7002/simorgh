"""Strict test bootstrap.

The project root is added explicitly, and the one known upstream AnyIO
DeprecationWarning is isolated before Starlette's TestClient import happens.
All other warnings remain errors through pytest.ini.
"""

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings(
    "ignore",
    message=r"The anyio\.abc\.BlockingPortal alias is deprecated, use anyio\.from_thread\.BlockingPortal instead\.",
    category=DeprecationWarning,
    module=r"anyio\._lazyimport",
)

try:
    import httpx2
except ImportError as exc:  # pragma: no cover - CI installs requirements-dev
    raise RuntimeError("httpx2 is required for the strict test suite") from exc

httpx2.alias_httpx()
