from __future__ import annotations

import time

from starlette.types import ASGIApp, Receive, Scope, Send

from .ledger import MotherLedger


class MotherActivityMiddleware:
    """Audit selected application activity without storing request content."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.ledger = MotherLedger()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        should_record = (
            method != "GET"
            and path not in {"/health"}
            and not path.startswith("/docs")
            and not path.startswith("/openapi")
        )
        started = time.perf_counter()
        status = 500
        if should_record:
            body = scope.get("query_string", b"")[:256]
        else:
            body = b""
        async def capture(message):
            nonlocal status
            if message.get("type") == "http.response.start":
                status = int(message.get("status", 500))
            await send(message)
        try:
            await self.app(scope, receive, capture)
        finally:
            if should_record:
                self.ledger.record_event(
                    component="simorgh",
                    event_type="http_request",
                    actor="user_or_client",
                    action=method,
                    severity="error" if status >= 500 else ("warning" if status >= 400 else "info"),
                    verified=True,
                    provenance="application_audit",
                    data={
                        "path": path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        "query_bytes": body.decode("utf-8", errors="replace")[:256],
                    },
                )
