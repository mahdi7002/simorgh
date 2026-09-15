import asyncio

from core.body_limit import RequestBodyLimitMiddleware


def _run(app, body, headers=()):
    sent = []

    async def receive():
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": list(headers),
    }

    asyncio.run(app(scope, receive, send))
    return sent


def test_body_limit_rejects_declared_oversize():
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    middleware = RequestBodyLimitMiddleware(app, max_body_size=10)

    sent = _run(
        middleware,
        b"x",
        headers=[(b"content-length", b"11")],
    )

    assert called is False
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_body_limit_rejects_streamed_oversize():
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True
        await receive()

    middleware = RequestBodyLimitMiddleware(app, max_body_size=10)

    sent = _run(middleware, b"01234567890")

    assert called is True
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_body_limit_allows_small_body():
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True
        message = await receive()
        assert message["body"] == b"12345"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"ok",
            }
        )

    middleware = RequestBodyLimitMiddleware(app, max_body_size=10)

    sent = _run(middleware, b"12345")

    assert called is True
    assert sent[0]["status"] == 200


def test_body_limit_preserves_non_http_scopes():
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    middleware = RequestBodyLimitMiddleware(app, max_body_size=10)

    sent = []

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        sent.append(message)

    asyncio.run(
        middleware(
            {"type": "lifespan"},
            receive,
            send,
        )
    )

    assert called is True
    assert sent == []


def test_body_limit_rejects_when_multiple_chunks_exceed_limit():
    called = False
    sent = []

    chunks = [
        {
            "type": "http.request",
            "body": b"123456",
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"78901",
            "more_body": False,
        },
    ]

    async def app(scope, receive, send):
        nonlocal called
        called = True
        await receive()
        await receive()

    async def receive():
        return chunks.pop(0)

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(app, max_body_size=10)

    asyncio.run(
        middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/test",
                "headers": [],
            },
            receive,
            send,
        )
    )

    assert called is True
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
