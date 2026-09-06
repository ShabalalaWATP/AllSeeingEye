"""Authentication and admission happen before reading a bounded, cancellable upload stream."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ase.api.deps import get_access_claims, get_container, get_current_user, get_session
from ase.api.errors import register_error_handlers
from ase.api.routers import research_inputs
from ase.application.dto import AccessClaims
from ase.domain.errors import Unauthenticated
from research_input_helpers import Harness


def upload_app(harness: Harness, *, authenticated: bool = True) -> FastAPI:
    application = FastAPI()
    application.include_router(research_inputs.router, prefix="/api")
    register_error_handlers(application)

    async def user() -> Any:
        if not authenticated:
            raise Unauthenticated()
        return harness.actor

    async def session() -> AsyncIterator[None]:
        yield None

    async def active_family(*args: Any, **kwargs: Any) -> bool:
        return True

    application.dependency_overrides[get_access_claims] = lambda: AccessClaims(
        harness.actor.id,
        harness.actor.role,
        "fixture",
        harness.clock.now() + timedelta(minutes=15),
        uuid4(),
        harness.actor.security_version,
    )

    application.dependency_overrides[get_current_user] = user
    application.dependency_overrides[get_session] = session
    application.dependency_overrides[get_container] = lambda: SimpleNamespace(
        import_research_input=lambda _: harness.service,
        session_factory=asynccontextmanager(session),
        repositories=lambda _: SimpleNamespace(
            users=harness.identity, refresh_tokens=SimpleNamespace(family_is_active=active_family)
        ),
        clock=harness.clock,
    )
    return application


def scope() -> dict[str, Any]:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/research/inputs",
        "raw_path": b"/api/research/inputs",
        "query_string": b"filename=notes.txt",
        "headers": [(b"content-type", b"application/octet-stream")],
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "root_path": "",
    }


@pytest.mark.parametrize("reason", ["unauthenticated", "capacity"])
async def test_rejected_request_does_not_read_a_single_body_chunk(reason: str) -> None:
    harness = Harness()
    application = upload_app(harness, authenticated=reason != "unauthenticated")
    if reason == "capacity":
        harness.store.reserve(harness.actor, "first.txt")
        harness.store.reserve(harness.actor, "second.txt")
    messages = []

    async def receive() -> dict[str, Any]:
        raise AssertionError("Body was read before authentication and admission.")

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await application(scope(), receive, send)
    assert messages[0]["status"] == (401 if reason == "unauthenticated" else 429)
    assert harness.extractor.calls == 0


async def test_successful_raw_upload_returns_typed_bounded_receipt() -> None:
    harness = Harness()
    async with AsyncClient(
        transport=ASGITransport(app=upload_app(harness)), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/research/inputs?filename=notes.txt",
            content=b"x" * 1100,
            headers={"Content-Type": "application/octet-stream"},
        )
    assert response.status_code == 201
    receipt = response.json()
    assert len(receipt["preview"]) == 1000 and receipt["extracted_characters"] == 1100
    assert len(receipt["sha256"]) == 64 and "events" not in receipt
    assert harness.extractor.calls == 1


async def test_route_caps_chunked_body_without_relying_on_content_length() -> None:
    harness = Harness()
    application = upload_app(harness)
    chunks = iter((b"x" * (4 * 1024 * 1024), b"x" * (4 * 1024 * 1024), b"x"))
    messages = []

    async def receive() -> dict[str, Any]:
        assert len(harness.store._reservations) == 1
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await application(scope(), receive, send)
    assert messages[0]["status"] == 413
    assert not harness.store._reservations and harness.extractor.calls == 0


async def test_cancelled_body_stream_releases_admitted_slot() -> None:
    harness = Harness()

    async def receive() -> dict[str, Any]:
        raise asyncio.CancelledError()

    async def send(message: dict[str, Any]) -> None:
        pass

    with pytest.raises(asyncio.CancelledError):
        await upload_app(harness)(scope(), receive, send)
    assert not harness.store._reservations and harness.extractor.calls == 0


async def test_disconnect_after_body_cancels_and_awaits_extraction_cleanup() -> None:
    harness = Harness()
    started, cleaned = asyncio.Event(), asyncio.Event()

    async def extract(*args: Any) -> Any:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    harness.extractor.extract = extract
    body_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": b"private", "more_body": False}
        await started.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        pass

    with pytest.raises(asyncio.CancelledError):
        await upload_app(harness)(scope(), receive, send)
    assert cleaned.is_set() and not harness.store._reservations


async def test_slow_body_is_bounded_and_releases_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = Harness()
    monkeypatch.setattr(research_inputs, "BODY_TIMEOUT_SECONDS", 0.001)
    messages = []

    async def receive() -> dict[str, Any]:
        await asyncio.Event().wait()
        raise AssertionError("Unreachable")

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await upload_app(harness)(scope(), receive, send)
    assert messages[0]["status"] == 422
    assert not harness.store._reservations and harness.extractor.calls == 0


async def test_multipart_is_refused_without_invoking_a_parser() -> None:
    harness = Harness()
    async with AsyncClient(
        transport=ASGITransport(app=upload_app(harness)), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/research/inputs?filename=notes.txt", files={"file": ("notes.txt", b"private")}
        )
    assert response.status_code == 422 and harness.extractor.calls == 0
    assert not harness.store._reservations
