"""Detection of a local OpenAI-compatible inference backend."""
from __future__ import annotations

import os
import shutil
import urllib.request
from typing import Any


def _url_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def discover_backend() -> dict[str, Any]:
    fast_url = os.environ.get("SIMORGH_LLM_FAST_URL", "http://127.0.0.1:8080/v1/chat/completions")
    models_url = os.environ.get("SIMORGH_LLM_FAST_MODELS_URL", "http://127.0.0.1:8080/v1/models")
    binaries = [
        shutil.which("llama-server"),
        str((__import__("pathlib").Path(__file__).resolve().parents[1] / "bin" / "llama-server")),
    ]
    binary = next((p for p in binaries if p and os.path.isfile(p) and os.access(p, os.X_OK)), None)
    endpoint_up = _url_ok(models_url)
    return {
        "provider": "openai-compatible",
        "endpoint": fast_url,
        "models_endpoint": models_url,
        "endpoint_up": endpoint_up,
        "llama_server_binary": binary,
        "ready": endpoint_up,
        "note": "مدل و backend دو مؤلفهٔ جدا هستند؛ نصب مدل بدون backend به‌تنهایی inference را فعال نمی‌کند.",
    }


__all__ = ["discover_backend"]
