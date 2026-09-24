from __future__ import annotations

import os
from typing import Any


def prepare_local_model_environment() -> dict[str, Any]:
    """Load persisted local backend URLs without requiring network access."""
    try:
        from core.user_runtime import load_config
        config = load_config()
    except Exception as exc:
        return {"status": "NOT_AVAILABLE", "reason": type(exc).__name__}

    mapping = {
        "llm_fast_url": "SIMORGH_LLM_FAST_URL",
        "llm_fast_models_url": "SIMORGH_LLM_FAST_MODELS_URL",
        "llm_quality_url": "SIMORGH_LLM_QUALITY_URL",
        "llm_quality_models_url": "SIMORGH_LLM_QUALITY_MODELS_URL",
    }
    applied = {}
    for key, env_name in mapping.items():
        value = config.get(key)
        if isinstance(value, str) and value:
            os.environ[env_name] = value
            applied[key] = value
    return {
        "status": "READY" if applied else "NOT_AVAILABLE",
        "applied": applied,
    }
