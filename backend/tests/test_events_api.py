"""Events, stream and admin source endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ase.adapters.persistence.base import Base
from ase.application.feeds.streams import StreamLimiter
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.events import Category, Point
from ase.domain.users import User
from ase.infrastructure.settings import Settings
from ase.main import create_app
from feeds_helpers import NOW, FakeConnector, make_event, make_spec
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    login_token,
)


@pytest.fixture
async def app(settings: Settings, clock: FakeClock, email_sender: object) -> AsyncIterator[FastAPI]:

    connector = FakeConnector(make_spec("fake_feed"))
    application = create_app(settings, clock=clock, connectors=[connector])  # type: ignore[arg-type]
    container: Container = application.state.container
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield application
    await container.dispose()


async def test_events_query_and_get(client: AsyncClient, container: Container, user: User) -> None:
    container.store.upsert(
        [
            make_event("q", category=Category.DISASTER, point=Point(10, 50), country_iso="DE"),
            make_event("k", category=Category.CYBER, point=None),
        ]
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    everything = await client.get("/api/events", headers=bearer(token))
    assert everything.status_code == 200
    assert everything.json()["count"] == 2
    item = everything.json()["items"][0]
    assert set(item) >= {"id", "category", "grade", "point", "attributes", "published_at"}
    filtered = await client.get(
        "/api/events",
        params={"categories": "disaster", "bbox": "0,40,20,60", "country": "de"},
        headers=bearer(token),
    )
    assert [e["subtype"] for e in filtered.json()["items"]] == ["earthquake"]
    since = await client.get(
        "/api/events",
        params={"since": (NOW + timedelta(hours=1)).isoformat()},
        headers=bearer(token),
    )
    assert since.json()["count"] == 0
    one = await client.get(f"/api/events/{item['id']}", headers=bearer(token))
    assert one.status_code == 200
    assert (await client.get("/api/events/nope", headers=bearer(token))).status_code == 404
    stats = await client.get("/api/events/stats", headers=bearer(token))
    assert stats.json()["total"] == 2
    assert (await client.get("/api/events")).status_code == 401


async def test_events_query_validation(client: AsyncClient, user: User) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    bad_category = await client.get(
        "/api/events", params={"categories": "weather"}, headers=bearer(token)
    )
    assert bad_category.status_code == 422
    assert bad_category.json()["error"]["fields"] == {"categories": "Unknown category"}
    bad_bbox = await client.get("/api/events", params={"bbox": "1,2"}, headers=bearer(token))
    assert bad_bbox.status_code == 422
    out_of_range = await client.get(
        "/api/events", params={"bbox": "0,80,10,-80"}, headers=bearer(token)
    )
    assert out_of_range.status_code == 422
    assert (
        await client.get("/api/events", params={"limit": 5000}, headers=bearer(token))
    ).status_code == 422


async def test_stream_delivers_upserts_and_expiries(
    app: FastAPI, container: Container, user: User, clock: FakeClock
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await login_token(client, USER_EMAIL, USER_PASSWORD)

        async def publish_later() -> None:
            await asyncio.sleep(0.05)
            await container.bus.publish(
                BusMessage(
                    "event.upsert",
                    {
                        "source_id": "fake_feed",
                        "events": [make_event("s", category=Category.CYBER)],
                    },
                )
            )
            await container.bus.publish(BusMessage("event.upsert", {"events": [make_event("d")]}))
            await container.bus.publish(BusMessage("event.expire", {"ids": ("x",), "count": 1}))
            await container.bus.publish(
                BusMessage("source.health", {"health": container.health.get("fake_feed")})
            )

        async def end_stream_later() -> None:
            # The transport buffers the whole response, so expire the token after the
            # messages went out and nudge the generator awake; it then says goodbye.
            await asyncio.sleep(0.2)
            clock.advance(timedelta(minutes=16))
            await container.bus.publish(BusMessage("event.expire", {"ids": (), "count": 0}))

        publisher = asyncio.create_task(publish_later())
        closer = asyncio.create_task(end_stream_later())
        response = await client.get(
            "/api/stream", params={"categories": "disaster"}, headers=bearer(token)
        )
        await publisher
        await closer
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-store"
        received: list[tuple[str, dict]] = []
        current_event = ""
        for line in response.text.splitlines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                received.append((current_event, json.loads(line.split(":", 1)[1])))
        kinds = [kind for kind, _ in received]
        assert kinds[:4] == ["hello", "event.upsert", "event.expire", "source.health"]
        assert kinds[-1] == "bye"
        # The cyber event was filtered out; the disaster event came through.
        assert received[1][1]["events"][0]["category"] == "disaster"
        assert received[2][1]["ids"] == ["x"]
        assert received[3][1]["source_id"] == "fake_feed"


async def test_stream_refuses_an_expired_token(app: FastAPI, clock: FakeClock, user: User) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await login_token(client, USER_EMAIL, USER_PASSWORD)
        clock.advance(timedelta(minutes=16))
        response = await client.get("/api/stream", headers=bearer(token))
        assert response.status_code == 401
        assert (await client.get("/api/stream")).status_code == 401


async def test_admin_sources_list_and_reset(client: AsyncClient, admin: User, user: User) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    listed = await client.get("/api/admin/sources", headers=bearer(token))
    assert listed.status_code == 200
    items = listed.json()["items"]
    feed = next(item for item in items if item["id"] == "fake_feed")
    assert feed["health"]["status"] == "idle"
    assert feed["poll_interval_seconds"] == 60
    assert any(not item["test_available"] for item in items)
    reset = await client.post("/api/admin/sources/fake_feed/reset", headers=bearer(token))
    assert reset.status_code == 200
    assert reset.json()["status"] == "idle"
    assert (
        await client.post("/api/admin/sources/nope/reset", headers=bearer(token))
    ).status_code == 404
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.get("/api/admin/sources", headers=bearer(user_token))).status_code == 403


async def test_stream_honours_the_token_expiry_and_the_per_user_cap(
    app: FastAPI, container: Container, user: User, clock: FakeClock
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await login_token(client, USER_EMAIL, USER_PASSWORD)
        container.streams = StreamLimiter(0)
        blocked = await client.get("/api/stream", headers=bearer(token))
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == "15"
        container.streams = StreamLimiter()

        # Opened ten minutes into a fifteen-minute token, the stream lives five more minutes.
        clock.advance(timedelta(minutes=10))

        async def end_stream_later() -> None:
            await asyncio.sleep(0.2)
            clock.advance(timedelta(minutes=6))
            await container.bus.publish(BusMessage("event.expire", {"ids": (), "count": 0}))

        closer = asyncio.create_task(end_stream_later())
        response = await client.get("/api/stream", headers=bearer(token))
        await closer
        assert response.status_code == 200
        first = next(line for line in response.text.splitlines() if line.startswith("data:"))
        assert json.loads(first.split(":", 1)[1]) == {"expires_in": 300}
        assert response.text.rstrip().endswith('{"reason": "token_expired"}')
        assert container.streams.held(user.id) == 0
