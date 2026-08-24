# -*- coding: utf-8 -*-
"""
core/llm_local.py
اتصال دومدلی: qwen2.5-1.5b (سریع، پیش‌فرض) روی 8080،
gemma-3-4b (دقیق‌تر، برای آیه/شعر/قصه) روی 8081.
"""
import logging
import re
import requests
from typing import Optional

logger = logging.getLogger(__name__)
FAST_URL = "http://127.0.0.1:8080/v1/chat/completions"
QUALITY_URL = "http://127.0.0.1:8081/v1/chat/completions"


def generate(system_prompt: str, user_message: str, max_tokens: int = 350,
             needs_quality: bool = False) -> Optional[str]:
    url = QUALITY_URL if needs_quality else FAST_URL
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
            timeout=120,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        return text
    except Exception as e:
        logger.error(f"خطا در اتصال به llama-server ({url}): {e}")
        if needs_quality:
            logger.info("تلاش مجدد با مدل سریع...")
            return generate(system_prompt, user_message, max_tokens, needs_quality=False)
        return None
