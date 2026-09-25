from __future__ import annotations

from typing import Any

import requests


def count_input_tokens(
    messages: list[dict[str, Any]],
    base_url: str,
    model: str | None = None,
    timeout: float = 15.0,
) -> int | None:
    payload: dict[str, Any] = {
        "messages": messages,
    }

    if model:
        payload["model"] = model

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions/input_tokens",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()

        data = response.json()
        value = data.get("input_tokens")

        if value is None:
            return None

        return int(value)

    except Exception:
        return None


def budget_for(
    n_ctx: int,
    task_class: str = "general",
    requested_output: int = 128,
    input_tokens: int | None = None,
) -> dict[str, Any]:
    n_ctx = max(512, int(n_ctx or 4096))
    requested_output = max(32, int(requested_output))

    safety_reserve = max(
        64,
        int(n_ctx * 0.05),
    )

    role_limits = {
        "heartbeat": min(256, int(n_ctx * 0.20)),
        "general": min(1536, int(n_ctx * 0.40)),
        "report": min(2048, int(n_ctx * 0.50)),
        "review": min(2048, int(n_ctx * 0.50)),
        "coding": min(2048, int(n_ctx * 0.50)),
        "deep": min(3072, int(n_ctx * 0.75)),
        "emergency": max(
            256,
            n_ctx - safety_reserve - requested_output,
        ),
    }

    role_limit = role_limits.get(
        task_class,
        role_limits["general"],
    )

    absolute_input_ceiling = max(
        256,
        n_ctx - safety_reserve - requested_output,
    )

    input_ceiling = min(
        role_limit,
        absolute_input_ceiling,
    )

    if input_tokens is None:
        within_budget = None
        remaining_input = None
        status = "UNKNOWN"
    else:
        input_tokens = int(input_tokens)
        within_budget = input_tokens <= input_ceiling
        remaining_input = input_ceiling - input_tokens
        status = "ALLOW" if within_budget else "REJECT"

    return {
        "n_ctx": n_ctx,
        "safety_reserve": safety_reserve,
        "requested_output": requested_output,
        "role_limit": role_limit,
        "absolute_input_ceiling": absolute_input_ceiling,
        "input_ceiling": input_ceiling,
        "task_class": task_class,
        "input_tokens": input_tokens,
        "remaining_input": remaining_input,
        "within_budget": within_budget,
        "status": status,
    }
