"""Resuming a live stream with Last-Event-ID instead of reloading the snapshot."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.types import Message, Receive, Scope, Send

from ase.adapters.bus.replay import MAX_REPLAY_MESSAGES
from ase.api.routers import stream as stream_router
from ase.api.stream_resume import StreamCursor, StreamPosition, parse_event_id
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.events import Category
from ase.domain.users import User
from ase.domain.warning import Alert
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, csrf_headers, login_token

Frames = AsyncIterator[dict[str, str]]


async def _open(
    client: AsyncClient, container: Container, user: User, last_id: str | None = None, **kw: Any
) -> Frames:
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    response = await stream_router.stream(user, claims, container, last_event_id=last_id, **kw)
    return response.body_iterator  # type: ignore[return-value]


async def _next(frames: Frames) -> dict[str, str]:
    async with asyncio.timeout(2):
        return await anext(frames)


def _upsert(key: str, category: Category = Category.DISASTER) -> BusMessage:
    return BusMessage("event.upsert", {"events": [make_event(key, category=category)]})


def _ids(frame: dict[str, str]) -> list[str]:
    return [event["id"] for event in json.loads(frame["data"])["events"]]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("abc", None),
        ("xyz-1", None),
        ("abc-01", None),
        ("abc--1", None),
        ("abc-1 ", None),
        ("ABC-1", None),
        ("a" * 60 + "-12345", None),
        ("abc-" + "9" * 19, None),
        ("abc123-0", StreamPosition("abc123", 0)),
        ("0f-42", StreamPosition("0f", 42)),
    ],
)
def test_untrusted_ids_are_validated(value: str | None, expected: StreamPosition | None) -> None:
    assert parse_event_id(value) == expected


async def test_resume_replays_missed_public_messages_through_the_filter(
    client: AsyncClient, container: Container, user: User
) -> None:
    bus, disaster = container.bus, Category.DISASTER.value
    first = await _open(client, container, user, categories=disaster)
    try:
        hello = await _next(first)
        assert hello["id"] == f"{bus.epoch}-{bus.last_sequence}"
        assert json.loads(hello["data"])["resumed"] is False
        await bus.publish(_upsert("seen"))
        seen = await _next(first)
        assert seen["id"] == f"{bus.epoch}-{bus.last_sequence}"
    finally:
        await first.aclose()
    await bus.publish(_upsert("filtered", Category.CYBER))
    await bus.publish(_upsert("missed"))
    alert = Alert(**_alert_fields(container, user))
    await bus.publish(BusMessage("alert", {"alert": alert}))
    await bus.publish(BusMessage("event.expire", {"ids": ["gone"]}))
    await bus.publish(BusMessage("source.health", {"health": container.health.get("fake_feed")}))
    start = bus.last_sequence
    resumed = await _open(client, container, user, seen["id"], categories=disaster)
    try:
        hello = await _next(resumed)
        assert json.loads(hello["data"])["resumed"] is True
        assert hello["id"] == seen["id"]
        replay = [await _next(resumed) for _ in range(3)]
        assert [frame["event"] for frame in replay] == [
            "event.upsert",
            "event.expire",
            "source.health",
        ]
        assert _ids(replay[0]) == [make_event("missed").id]
        # Private alerts are never replayed, and the last replayed frame covers them.
        assert replay[-1]["id"] == f"{bus.epoch}-{start}"
        await bus.publish(_upsert("live"))
        live = await _next(resumed)
        assert _ids(live) == [make_event("live").id]
        assert live["id"] == f"{bus.epoch}-{start + 1}"
    finally:
        await resumed.aclose()
    assert container.streams.held(user.id) == 0


def _alert_fields(container: Container, user: User) -> dict[str, Any]:
    return {
        "id": uuid4(),
        "indicator_id": None,
        "fired_at": container.clock.now(),
        "title": "Own alert",
        "summary": "",
        "count": 1,
        "threshold": 1,
        "event_ids": (),
        "countries": (),
        "created_by": user.id,
    }


async def test_resume_with_nothing_missed_starts_at_the_live_position(
    client: AsyncClient, container: Container, user: User
) -> None:
    bus = container.bus
    await bus.publish(BusMessage("alert", {"alert": Alert(**_alert_fields(container, user))}))
    position = f"{bus.epoch}-{bus.last_sequence - 1}"
    frames = await _open(client, container, user, position)
    try:
        hello = await _next(frames)
        assert json.loads(hello["data"])["resumed"] is True
        assert hello["id"] == f"{bus.epoch}-{bus.last_sequence}"
    finally:
        await frames.aclose()


@pytest.mark.parametrize("kind", ["garbage", "other_epoch", "future", "evicted"])
async def test_unresumable_positions_request_a_snapshot(
    client: AsyncClient, container: Container, user: User, kind: str
) -> None:
    bus = container.bus
    await bus.publish(BusMessage("event.expire", {"ids": []}))
    last_id = {
        "garbage": "not an id",
        "other_epoch": f"{'0' * 12}-{bus.last_sequence}",
        "future": f"{bus.epoch}-{bus.last_sequence + 1}",
        "evicted": f"{bus.epoch}-{bus.last_sequence - 1}",
    }[kind]
    if kind == "evicted":
        for _ in range(MAX_REPLAY_MESSAGES):
            bus.publish_nowait(BusMessage("event.expire", {"ids": []}))
    frames = await _open(client, container, user, last_id)
    try:
        hello = await _next(frames)
        assert json.loads(hello["data"])["resumed"] is False
        resync = await _next(frames)
        assert resync["event"] == "event.resync"
        assert json.loads(resync["data"]) == {"reason": "snapshot_required"}
        assert resync["id"] == hello["id"] == f"{bus.epoch}-{bus.last_sequence}"
        await bus.publish(_upsert("after"))
        assert (await _next(frames))["event"] == "event.upsert"
    finally:
        await frames.aclose()


async def test_resume_keeps_the_opening_session_check(
    client: AsyncClient, container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads = 0
    original = stream_router._stream_access

    async def counted(*args: Any) -> Any:
        nonlocal reads
        reads += 1
        return await original(*args)

    monkeypatch.setattr(stream_router, "_stream_access", counted)
    bus = container.bus
    position = f"{bus.epoch}-{bus.last_sequence}"
    await bus.publish(_upsert("missed"))
    frames = await _open(client, container, user, position)
    logout = await client.post("/api/auth/logout", headers=csrf_headers(client))
    assert logout.status_code == 204
    try:
        bye = await _next(frames)
        assert bye == {"event": "bye", "data": '{"reason": "session_revoked"}'}
        with pytest.raises(StopAsyncIteration):
            await _next(frames)
    finally:
        await frames.aclose()
    assert reads == 1


async def test_replayed_messages_pass_the_same_rechecks(
    client: AsyncClient, container: Container, user: User
) -> None:
    bus = container.bus
    position = f"{bus.epoch}-{bus.last_sequence}"
    for key in ("one", "two", "three"):
        await bus.publish(_upsert(key))
    frames = await _open(client, container, user, position)
    try:
        assert json.loads((await _next(frames))["data"])["resumed"] is True
        assert _ids(await _next(frames)) == [make_event("one").id]
        await client.post("/api/auth/logout", headers=csrf_headers(client))
        bye = await _next(frames)
        assert bye["event"] == "bye" and "session_revoked" in bye["data"]
    finally:
        await frames.aclose()


async def test_skipped_positions_are_checkpointed_without_an_event(
    client: AsyncClient, container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stream_router, "PING_SECONDS", 0.01)
    bus = container.bus
    frames = await _open(client, container, user, categories=Category.DISASTER.value)
    try:
        await _next(frames)
        await bus.publish(_upsert("filtered", Category.CYBER))
        # An idle wake records the new position with an id-only frame.
        assert await _next(frames) == {"id": f"{bus.epoch}-{bus.last_sequence}"}
    finally:
        await frames.aclose()


def test_cursor_checkpoints_only_moved_positions() -> None:
    now, interval = make_event().observed_at, timedelta(seconds=15)
    cursor = StreamCursor("ab", 3, now, interval)
    assert cursor.frame("hello", "{}", now) == {"event": "hello", "id": "ab-3", "data": "{}"}
    assert cursor.checkpoint(now, idle=True) is None
    cursor.advance(2)
    cursor.advance(5)
    assert cursor.position == 5
    assert cursor.checkpoint(now + timedelta(seconds=14), idle=False) is None
    assert cursor.checkpoint(now + interval, idle=False) == {"id": "ab-5"}
    cursor.advance(6)
    assert cursor.checkpoint(now + interval, idle=True) == {"id": "ab-6"}


@pytest.mark.parametrize("admission_delay", [0, 0.3], ids=["immediate", "delayed_authentication"])
async def test_last_event_id_header_resumes_over_http(
    app: FastAPI, container: Container, user: User, clock: FakeClock, admission_delay: float
) -> None:
    bus = container.bus
    replay_sent = asyncio.Event()

    async def delayed_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/api/stream":
            await app(scope, receive, send)
            return
        # Keep real authentication, but exercise admission later than the old 200ms closer.
        await asyncio.sleep(admission_delay)
        pending = b""

        async def observe_send(message: Message) -> None:
            nonlocal pending
            await send(message)
            if message["type"] != "http.response.body":
                return
            pending += message.get("body", b"")
            blocks = re.split(rb"(?:\r?\n){2}", pending)
            pending = blocks.pop()
            for block in blocks:
                fields = dict(line.split(b": ", 1) for line in block.splitlines() if b": " in line)
                if (
                    fields.get(b"event") == b"event.upsert"
                    and fields.get(b"id") == f"{bus.epoch}-{missed}".encode()
                ):
                    replay_sent.set()

        await app(scope, receive, observe_send)

    async with AsyncClient(
        transport=ASGITransport(app=delayed_app), base_url="http://test"
    ) as http:
        token = await login_token(http, USER_EMAIL, USER_PASSWORD)
        position = f"{bus.epoch}-{bus.last_sequence}"
        await bus.publish(_upsert("missed"))
        missed = bus.last_sequence

        async def end_stream_later() -> None:
            async with asyncio.timeout(5):
                await replay_sent.wait()
            clock.advance(timedelta(minutes=16))
            await bus.publish(BusMessage("event.expire", {"ids": []}))

        closer = asyncio.create_task(end_stream_later())
        try:
            async with asyncio.timeout(10):
                response = await http.get(
                    "/api/stream", headers={**bearer(token), "Last-Event-ID": position}
                )
                assert response.status_code == 200
                await closer
        finally:
            closer.cancel()
            await asyncio.gather(closer, return_exceptions=True)
    assert replay_sent.is_set()
    assert container.streams.held(user.id) == 0
    frames = []
    for block in re.split(r"(?:\r?\n){2}", response.text):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            frames.append(fields)
    assert [frame["event"] for frame in frames] == ["hello", "event.upsert", "bye"]
    assert frames[0]["id"] == position and json.loads(frames[0]["data"])["resumed"] is True
    assert frames[1]["id"] == f"{bus.epoch}-{missed}"
    assert _ids(frames[1]) == [make_event("missed").id]
    assert json.loads(frames[2]["data"]) == {"reason": "token_expired"}
