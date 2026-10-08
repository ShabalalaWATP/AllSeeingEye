"""Events, stream and admin source endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sse_starlette.sse import EventSourceResponse

from ase.api.routers import stream as stream_router
from ase.application.feeds.streams import StreamLimiter
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.events import Category, Point
from ase.domain.news_time import news_index_date
from ase.domain.users import User
from event_app_fixtures import email_sender, feed_connectors  # noqa: F401
from feeds_helpers import NOW, make_event
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    bearer,
    login_token,
)

Frames = AsyncIterator[dict[str, str]]


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


async def test_map_news_indexing_window_does_not_change_publication_queries(
    client: AsyncClient, container: Container, user: User
) -> None:
    indexed = make_event("indexed", category=Category.NEWS, published_at=None).with_changes(
        source_id="gdelt_news", source_dates=(news_index_date(NOW.strftime("%Y%m%d%H%M%S")),)
    )
    undated = make_event("unknown", category=Category.NEWS, published_at=None)
    container.store.upsert([indexed, undated])
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    params = {"categories": "news", "since": (NOW - timedelta(hours=1)).isoformat()}
    ordinary = await client.get("/api/events", params=params, headers=bearer(token))
    assert ordinary.json()["count"] == 0
    mapped = await client.get(
        "/api/events",
        params={**params, "time_basis": "map_record_time", "sampling": "geographic"},
        headers=bearer(token),
    )
    assert mapped.status_code == 200
    assert [item["id"] for item in mapped.json()["items"]] == [indexed.id]
    assert mapped.json()["items"][0]["published_at"] is None
    assert (
        await client.get(
            "/api/events", params={**params, "time_basis": "observed_at"}, headers=bearer(token)
        )
    ).status_code == 422


async def test_military_filter_precedes_page_limit_and_pagination_is_bounded(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    container.store.upsert(
        [
            make_event("civil", category=Category.AVIATION),
            make_event(
                "military",
                category=Category.AVIATION,
                subtype="military_aircraft",
                published_at=NOW - timedelta(seconds=30),
            ),
        ]
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get(
        "/api/events",
        params={"categories": "aviation", "military": "true", "limit": 1},
        headers=bearer(token),
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["subtype"] == "military_aircraft"
    second = await client.get(
        "/api/events",
        params={"categories": "aviation", "offset": 1, "limit": 1},
        headers=bearer(token),
    )
    assert second.json()["items"][0]["subtype"] == "military_aircraft"
    for offset in (-1, 15001):
        assert (
            await client.get("/api/events", params={"offset": offset}, headers=bearer(token))
        ).status_code == 422


async def _open_stream(
    container: Container, user: User, token: str, **options: Any
) -> tuple[EventSourceResponse, Frames]:
    """Call the stream route directly and read frames as they are produced.

    Reading the body through the ASGI transport buffers the whole response, which
    forced real sleeps before advancing the clock. Frame-by-frame reads need none.
    """
    claims = container.issuer.verify(token)
    response = await stream_router.stream(user, claims, container, last_event_id=None, **options)
    return response, response.body_iterator  # type: ignore[return-value]


async def _next(frames: Frames) -> tuple[str, Any]:
    async with asyncio.timeout(2):
        frame = await anext(frames)
    return frame["event"], json.loads(frame["data"])


async def test_stream_delivers_upserts_and_expiries(
    client: AsyncClient, container: Container, user: User, clock: FakeClock
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response, frames = await _open_stream(container, user, token, categories="disaster")
    try:
        assert response.media_type == "text/event-stream"
        assert response.headers["cache-control"] == "no-store"
        assert (await _next(frames))[0] == "hello"
        bus = container.bus
        await bus.publish(
            BusMessage(
                "event.upsert",
                {"source_id": "fake_feed", "events": [make_event("s", category=Category.CYBER)]},
            )
        )
        await bus.publish(BusMessage("event.upsert", {"events": [make_event("d")]}))
        await bus.publish(BusMessage("event.expire", {"ids": ("x",), "count": 1}))
        await bus.publish(
            BusMessage("source.health", {"health": container.health.get("fake_feed")})
        )
        # The cyber event was filtered out; the disaster event came through.
        kind, upsert = await _next(frames)
        assert kind == "event.upsert" and upsert["events"][0]["category"] == "disaster"
        assert await _next(frames) == ("event.expire", {"ids": ["x"], "count": 1})
        kind, health = await _next(frames)
        assert kind == "source.health" and health["source_id"] == "fake_feed"
        # Once the token has expired, the next wake-up says goodbye.
        clock.advance(timedelta(minutes=16))
        await bus.publish(BusMessage("event.expire", {"ids": (), "count": 0}))
        assert await _next(frames) == ("bye", {"reason": "token_expired"})
    finally:
        await frames.aclose()
    assert container.streams.held(user.id) == 0


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
        _response, frames = await _open_stream(container, user, token)
        try:
            assert await _next(frames) == ("hello", {"expires_in": 300, "resumed": False})
            clock.advance(timedelta(minutes=6))
            await container.bus.publish(BusMessage("event.expire", {"ids": (), "count": 0}))
            assert await _next(frames) == ("bye", {"reason": "token_expired"})
        finally:
            await frames.aclose()
        assert container.streams.held(user.id) == 0
