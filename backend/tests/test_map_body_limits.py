"""Map JSON allowances remain bounded and cannot widen other endpoint limits."""

from uuid import uuid4

import pytest
from starlette.types import Message

from ase.api.middleware import MAP_VIEW_MAX_BODY_BYTES, BodySizeLimitMiddleware


async def send_body(path, method, chunks, declared=None):
    seen, responses = [], []

    async def application(scope, receive, send):
        while True:
            item = await receive()
            seen.append(item.get("body", b""))
            if not item.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    messages: list[Message] = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]

    async def receive():
        return messages.pop(0)

    async def send(message):
        responses.append(message)

    scope = {
        "type": "http",
        "path": path,
        "method": method,
        "headers": [] if declared is None else [(b"content-length", str(declared).encode())],
    }
    await BodySizeLimitMiddleware(application)(scope, receive, send)
    return responses[0]["status"], seen


@pytest.mark.parametrize(
    "method,path", [("POST", "/api/map/views"), ("PATCH", f"/api/map/views/{uuid4()}")]
)
async def test_saved_map_accepts_bounded_chunked_geometry_above_ordinary_limit(method, path):
    chunks = [b"x" * 40000, b"y" * 40000]
    status, seen = await send_body(path, method, chunks)
    assert status == 204 and seen == chunks


@pytest.mark.parametrize("declared", [None, MAP_VIEW_MAX_BODY_BYTES + 1])
async def test_map_body_cap_covers_declared_and_chunked_requests(declared):
    status, seen = await send_body(
        "/api/map/views", "POST", [b"x" * (MAP_VIEW_MAX_BODY_BYTES + 1)], declared
    )
    assert status == 413 and seen == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/research/plan"),
        ("GET", "/api/map/views"),
        ("POST", "/api/map/views/extra"),
        ("PATCH", "/api/map/views/not-a-uuid"),
        ("PATCH", f"/api/map/views/{uuid4()}/revisions"),
    ],
)
async def test_large_body_allowance_is_limited_to_exact_save_routes(method, path):
    status, seen = await send_body(path, method, [b"x" * 65537])
    assert status == 413 and seen == []
