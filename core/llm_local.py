from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional

import requests

from core.mother.brain_registry import discover_local_brain
from core.mother.context_governor import budget_for, count_input_tokens

logger = logging.getLogger(__name__)

FAST_URL = os.environ.get(
    "SIMORGH_LLM_FAST_URL",
    "http://127.0.0.1:8080/v1/chat/completions",
)
QUALITY_URL = os.environ.get(
    "SIMORGH_LLM_QUALITY_URL",
    "http://127.0.0.1:8081/v1/chat/completions",
)

FAST_TIMEOUT = float(os.getenv("SIMORGH_FAST_TIMEOUT", "60"))
QUALITY_TIMEOUT = float(os.getenv("SIMORGH_QUALITY_TIMEOUT", "120"))
REPORT_TIMEOUT = 180.0
REVIEW_TIMEOUT = 150.0

FAST_MODELS_URL = os.environ.get(
    "SIMORGH_LLM_FAST_MODELS_URL",
    "http://127.0.0.1:8080/v1/models",
)
QUALITY_MODELS_URL = os.environ.get(
    "SIMORGH_LLM_QUALITY_MODELS_URL",
    "http://127.0.0.1:8081/v1/models",
)

_LOCAL_PREPARE_INTERVAL = float(
    os.getenv("SIMORGH_LOCAL_PREPARE_INTERVAL", "15")
)
_LAST_LOCAL_PREPARE = 0.0

_PARAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[bB]\b")


def _fast_url() -> str:
    return os.environ.get("SIMORGH_LLM_FAST_URL", FAST_URL)


def _quality_url() -> str:
    return os.environ.get("SIMORGH_LLM_QUALITY_URL", QUALITY_URL)


def _fast_models_url() -> str:
    return os.environ.get("SIMORGH_LLM_FAST_MODELS_URL", FAST_MODELS_URL)


def _quality_models_url() -> str:
    return os.environ.get(
        "SIMORGH_LLM_QUALITY_MODELS_URL",
        QUALITY_MODELS_URL,
    )


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
        logger.warning(
            "آماده‌سازی مدل محلی شکست خورد: %s",
            type(exc).__name__,
        )


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


def generate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 350,
    needs_quality: bool = False,
    task_class: str = "general",
) -> Optional[str]:
    _prepare_offline_first()

    if task_class == "report":
        timeout = REPORT_TIMEOUT
    elif task_class == "review":
        timeout = REVIEW_TIMEOUT
    else:
        timeout = QUALITY_TIMEOUT if needs_quality else FAST_TIMEOUT

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    brain = discover_local_brain()

    if brain.get("status") != "READY":
        logger.error("مدل محلی در دسترس نیست")
        return None

    base_url = str(
        brain.get("base_url") or "http://127.0.0.1:8080"
    ).rstrip("/")

    n_ctx = int(brain.get("n_ctx") or 4096)

    model_id = str(
        brain.get("model") or ""
    ).strip()

    url = f"{base_url}/v1/chat/completions"

    input_tokens = count_input_tokens(
        messages,
        base_url,
        model_id or None,
    )

    if input_tokens is None:
        logger.error("نتوانستم تعداد token ورودی را از llama.cpp بگیرم")
        return None

    budget = budget_for(
        n_ctx=n_ctx,
        input_tokens=input_tokens,
        requested_output=max_tokens,
        task_class=task_class,
    )

    if budget["status"] != "ALLOW":
        logger.error(
            "Mother Context Governor rejected request: "
            "input=%s ceiling=%s class=%s n_ctx=%s",
            input_tokens,
            budget["input_ceiling"],
            task_class,
            n_ctx,
        )
        return None

    max_tokens = min(
        int(max_tokens),
        max(32, int(n_ctx - input_tokens - budget["safety_reserve"])),
    )

    model_id = str(brain.get("model") or "")
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "repeat_penalty": 1.15,
        "top_p": 0.9,
    }

    if model_id and model_id != "UNKNOWN":
        payload["model"] = model_id

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()

        data = resp.json()
        text = data["choices"][0]["message"]["content"]

        return re.sub(
            r"<think>.*?</think>",
            "",
            text,
            flags=re.S,
        ).strip()

    except requests.exceptions.HTTPError as exc:
        body = ""
        try:
            body = exc.response.text[:2000] if exc.response is not None else ""
        except Exception:
            pass

        logger.error(
            "llama-server HTTP error (%s): %s body=%s",
            url,
            exc,
            body,
        )
        return None

    except requests.exceptions.Timeout as exc:
        logger.error(
            "llama-server timeout (%s): %s",
            url,
            exc,
        )

        if needs_quality and _quality_url() != _fast_url():
            return generate(
                system_prompt,
                user_message,
                max_tokens=max_tokens,
                needs_quality=False,
                task_class=task_class,
            )

        return None

    except Exception as exc:
        logger.error(
            "خطا در اتصال به llama-server (%s): %s",
            url,
            exc,
        )

        if needs_quality and _quality_url() != _fast_url():
            return generate(
                system_prompt,
                user_message,
                max_tokens=max_tokens,
                needs_quality=False,
                task_class=task_class,
            )

        return None
