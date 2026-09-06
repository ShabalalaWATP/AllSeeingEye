"""HTTP authentication must not reserve a pooled connection for a live SSE response."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from starlette.types import Message, Scope

import ase.container as container_module
from ase.adapters.persistence.base import Base
from ase.application.dto import RequestContext
from ase.application.ports.feeds import BusMessage
from ase.infrastructure.settings import Settings
from ase.main import create_app
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, create_user


async def test_idle_http_stream_releases_authentication_connection(
    settings: Settings,
    clock: FakeClock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'stream-pool.db').as_posix()}"

    def bounded_engine(url: str) -> AsyncEngine:
        assert url == database_url
        return create_async_engine(url, pool_size=2, max_overflow=0, pool_timeout=1)

    monkeypatch.setattr(container_module, "create_engine", bounded_engine)
    app = create_app(settings.model_copy(update={"database_url": database_url}), clock=clock)
    container = app.state.container
    stream_task = None
    disconnect = asyncio.Event()
    try:
        async with container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
        async with container.session_factory() as session:
            auth = await container.login(session).execute(
                USER_EMAIL, USER_PASSWORD, RequestContext(ip="pool-test", user_agent=None)
            )
        hello, delivery = asyncio.Event(), asyncio.Event()
        request_received = False

        async def receive() -> Message:
            nonlocal request_received
            if not request_received:
                request_received = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            if message["type"] != "http.response.body":
                return
            body = message.get("body", b"")
            if b"event: hello" in body:
                hello.set()
            if b"event: event.expire" in body:
                delivery.set()

        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/stream",
            "raw_path": b"/api/stream",
            "root_path": "",
            "query_string": b"",
            "headers": [
                (b"host", b"test"),
                (b"authorization", f"Bearer {auth.access.token}".encode()),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        }
        # Calling the ASGI app exercises dependency teardown around the full response.
        # A direct stream() call cannot reproduce request-scoped session retention.
        stream_task = asyncio.create_task(app(scope, receive, send))
        await asyncio.wait_for(hello.wait(), 5)
        pool = container.engine.pool
        assert isinstance(pool, AsyncAdaptedQueuePool)
        assert pool.checkedout() == 0, "An idle SSE response retained its auth connection"
        assert not stream_task.done()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/me", headers=bearer(auth.access.token))
            assert response.status_code == 200
            assert response.json()["id"] == str(user.id)
        await container.bus.publish(BusMessage("event.expire", {"ids": ["fixture-event"]}))
        await asyncio.wait_for(delivery.wait(), 5)
        assert pool.checkedout() == 0
    finally:
        disconnect.set()
        try:
            if stream_task is not None:
                await asyncio.wait_for(stream_task, 5)
        finally:
            await container.dispose()
