import logging
import os
import re
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)
FAST_URL = os.environ.get("SIMORGH_LLM_FAST_URL", "http://127.0.0.1:8080/v1/chat/completions")
QUALITY_URL = os.environ.get("SIMORGH_LLM_QUALITY_URL", "http://127.0.0.1:8081/v1/chat/completions")
FAST_TIMEOUT = float(os.getenv("SIMORGH_FAST_TIMEOUT", "30"))
QUALITY_TIMEOUT = float(os.getenv("SIMORGH_QUALITY_TIMEOUT", "60"))
FAST_MODELS_URL = os.environ.get("SIMORGH_LLM_FAST_MODELS_URL", "http://127.0.0.1:8080/v1/models")
QUALITY_MODELS_URL = os.environ.get("SIMORGH_LLM_QUALITY_MODELS_URL", "http://127.0.0.1:8081/v1/models")

_PARAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[bB]\b")
_LAST_LOCAL_PREPARE = 0.0
_LOCAL_PREPARE_INTERVAL = float(os.getenv("SIMORGH_LOCAL_PREPARE_INTERVAL", "15"))


def _fast_url() -> str:
    return os.environ.get("SIMORGH_LLM_FAST_URL", FAST_URL)


def _quality_url() -> str:
    return os.environ.get("SIMORGH_LLM_QUALITY_URL", QUALITY_URL)


def _fast_models_url() -> str:
    return os.environ.get("SIMORGH_LLM_FAST_MODELS_URL", FAST_MODELS_URL)


def _quality_models_url() -> str:
    return os.environ.get("SIMORGH_LLM_QUALITY_MODELS_URL", QUALITY_MODELS_URL)


def _privacy_mode() -> str:
    env_mode = os.environ.get("SIMORGH_PRIVACY_MODE")
    if env_mode:
        return env_mode.strip().lower()
    try:
        from core.user_runtime import load_config

        mode = load_config().get("privacy_mode", "local-only")
        return str(mode).strip().lower() or "local-only"
    except Exception:
        return "local-only"


def _prepare_offline_first() -> None:
    """Prefer an already-running loopback model in local-only mode."""
    global _LAST_LOCAL_PREPARE

    if _privacy_mode() != "local-only":
        return

    now = time.monotonic()
    if now - _LAST_LOCAL_PREPARE < _LOCAL_PREPARE_INTERVAL:
        return

    _LAST_LOCAL_PREPARE = now
    try:
        from core.mother.local_model import prepare_local_model_environment

        result = prepare_local_model_environment()
        if result.get("status") == "READY":
            logger.info(
                "آفلاین‌اول: مدل محلی انتخاب شد: %s",
                result.get("models_endpoint") or result.get("endpoint"),
            )
    except Exception as exc:
        logger.warning("آماده‌سازی مدل محلی شکست خورد: %s", type(exc).__name__)


def get_model_tier(needs_quality: bool = False) -> str:
    _prepare_offline_first()
    url = _quality_models_url() if needs_quality else _fast_models_url()
    try:
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        model_id = (data.get("data") or [{}])[0].get("id", "")
        match = _PARAM_RE.search(model_id)
        if not match:
            return "small"
        params = float(match.group(1))
        if params < 2:
            return "small"
        if params <= 8:
            return "medium"
        return "large"
    except Exception:
        return "small"


def generate(system_prompt: str, user_message: str, max_tokens: int = 350, needs_quality: bool = False) -> Optional[str]:
    _prepare_offline_first()
    url = _quality_url() if needs_quality else _fast_url()
    timeout = QUALITY_TIMEOUT if needs_quality else FAST_TIMEOUT
    try:
        resp = requests.post(
            url,
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.5,
                "repeat_penalty": 1.15,
                "top_p": 0.9,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    except Exception as exc:
        logger.error("خطا در اتصال به llama-server (%s): %s", url, exc)
        if needs_quality:
            return generate(system_prompt, user_message, max_tokens, needs_quality=False)
        return None
