from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests


def _base_url(value: str) -> str:
    value = value.rsplit("/v1/", 1)[0]
    return value.rstrip("/")


def prepare_local_model_environment() -> dict[str, Any]:
    """Select an already-running local model endpoint without starting one."""
    candidates: list[str] = []
    try:
        from core.user_runtime import load_config
        config = load_config()
    except Exception:
        config = {}

    for key in ("llm_quality_models_url", "llm_fast_models_url"):
        value = config.get(key)
        if isinstance(value, str) and value:
            candidates.append(_base_url(value))

    for value in (
        os.environ.get("SIMORGH_LLM_QUALITY_MODELS_URL"),
        os.environ.get("SIMORGH_LLM_FAST_MODELS_URL"),
        "http://127.0.0.1:8080/v1/models",
    ):
        if value:
            candidates.append(_base_url(value))

    seen: set[str] = set()
    for base in candidates:
        parsed = urlparse(base)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            continue
        if base in seen:
            continue
        seen.add(base)
        models_url = f"{base}/v1/models"
        try:
            response = requests.get(models_url, timeout=2)
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data")
            if not isinstance(models, list) or not models:
                continue
        except Exception:
            continue

        endpoint = f"{base}/v1/chat/completions"
        os.environ["SIMORGH_LLM_FAST_URL"] = endpoint
        os.environ["SIMORGH_LLM_FAST_MODELS_URL"] = models_url
        os.environ["SIMORGH_LLM_QUALITY_URL"] = endpoint
        os.environ["SIMORGH_LLM_QUALITY_MODELS_URL"] = models_url
        model_ids = [
            item.get("id")
            for item in models
            if isinstance(item, dict) and item.get("id")
        ]
        return {
            "status": "READY",
            "endpoint": endpoint,
            "models_endpoint": models_url,
            "models": model_ids,
        }

    return {
        "status": "NOT_AVAILABLE",
        "reason": "no_running_local_llm_endpoint",
    }
