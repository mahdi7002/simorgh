from __future__ import annotations

import json
from typing import Any, Awaitable, Callable


class _BodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Pure ASGI request-body size limiter for SIMORGH."""

    def __init__(self, app: Callable[..., Awaitable[Any]], max_body_size: int):
        if max_body_size < 1:
            raise ValueError("max_body_size must be positive")
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def limited_send(message):
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }

        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except (TypeError, ValueError):
                declared_length = None

            if declared_length is not None and declared_length > self.max_body_size:
                await self._reject(send)
                return

        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()

            if message.get("type") != "http.request":
                return message

            body = message.get("body", b"")
            total += len(body)

            if total > self.max_body_size:
                raise _BodyTooLarge

            return message

        try:
            await self.app(scope, limited_receive, limited_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send)
                return
            raise

    async def _reject(self, send):
        body = json.dumps(
            {"detail": "Request body too large"},
            ensure_ascii=False,
        ).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
