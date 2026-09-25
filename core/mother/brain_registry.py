from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_QUALITY = "http://127.0.0.1:8081"
DEFAULT_FAST = "http://127.0.0.1:8080"


def _clean_base(value: str | None) -> str:
    return (value or "").strip().rstrip("/")


def _candidate_bases() -> list[str]:
    values = [
        _clean_base(
            os.getenv(
                "SIMORGH_MOTHER_QUALITY_BASE_URL",
                DEFAULT_QUALITY,
            )
        ),
        _clean_base(
            os.getenv(
                "SIMORGH_MOTHER_FAST_BASE_URL",
                DEFAULT_FAST,
            )
        ),
        DEFAULT_FAST,
    ]

    result: list[str] = []

    for base in values:
        if base and base not in result:
            result.append(base)

    return result


def _find_value(obj: Any, names: set[str]) -> Any:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in names:
                return value

        for value in obj.values():
            found = _find_value(value, names)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for value in obj:
            found = _find_value(value, names)
            if found is not None:
                return found

    return None


def _probe(base_url: str, timeout: float = 4.0) -> dict[str, Any]:
    try:
        models_response = requests.get(
            f"{base_url}/v1/models",
            timeout=timeout,
        )
        models_response.raise_for_status()

        data = models_response.json()
        models = data.get("data") or []

        if not isinstance(models, list) or not models:
            return {
                "backend": "llama.cpp",
                "base_url": base_url,
                "model": "UNKNOWN",
                "n_ctx": 4096,
                "n_ctx_train": None,
                "total_slots": None,
                "status": "NOT_AVAILABLE",
                "error": "No models returned",
            }

        first = models[0] if isinstance(models[0], dict) else {}
        model_id = str(first.get("id") or "UNKNOWN")

        props: dict[str, Any] = {}

        try:
            props_response = requests.get(
                f"{base_url}/props",
                timeout=timeout,
            )
            props_response.raise_for_status()
            candidate = props_response.json()

            if isinstance(candidate, dict):
                props = candidate
        except Exception:
            pass

        n_ctx = _find_value(props, {"n_ctx"})
        n_ctx_train = _find_value(props, {"n_ctx_train"})
        total_slots = _find_value(props, {"total_slots"})

        return {
            "backend": "llama.cpp",
            "base_url": base_url,
            "model": model_id,
            "n_ctx": int(n_ctx) if n_ctx is not None else 4096,
            "n_ctx_train": (
                int(n_ctx_train)
                if n_ctx_train is not None
                else None
            ),
            "total_slots": (
                int(total_slots)
                if total_slots is not None
                else None
            ),
            "status": "READY",
            "error": None,
        }

    except Exception as exc:
        return {
            "backend": "llama.cpp",
            "base_url": base_url,
            "model": "UNKNOWN",
            "n_ctx": 4096,
            "n_ctx_train": None,
            "total_slots": None,
            "status": "NOT_AVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
        }


def discover_local_brain() -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []

    for base_url in _candidate_bases():
        result = _probe(base_url)

        # IMPORTANT:
        # Never place `result` itself into its own `attempts`.
        attempts.append(dict(result))

        if result.get("status") == "READY":
            return {
                **result,
                "attempts": attempts,
            }

    return {
        "backend": "llama.cpp",
        "base_url": "",
        "model": "UNKNOWN",
        "n_ctx": 4096,
        "n_ctx_train": None,
        "total_slots": None,
        "status": "NOT_AVAILABLE",
        "error": "No reachable local model endpoint",
        "attempts": attempts,
    }
