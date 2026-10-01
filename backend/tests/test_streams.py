"""Per-user cap on live streams and per-stream filtering of bulk refresh hints."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from httpx import AsyncClient

from ase.adapters.bus.memory import MAX_UPSERT_EVENTS
from ase.api.routers import stream as stream_router
from ase.application.feeds.streams import StreamLimiter
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.events import Category
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import USER_PASSWORD, login_token


def test_limiter_counts_per_user() -> None:
    limiter = StreamLimiter(max_per_user=2)
    alice, bob = uuid4(), uuid4()
    assert limiter.acquire(alice) and limiter.acquire(alice)
    assert not limiter.acquire(alice)
    assert limiter.acquire(bob)
    assert limiter.held(alice) == 2 and limiter.held(bob) == 1
    limiter.release(alice)
    assert limiter.acquire(alice)
    limiter.release(alice)
    limiter.release(alice)
    limiter.release(alice)  # releasing below zero is harmless
    assert limiter.held(alice) == 0


async def test_bulk_hint_reaches_only_streams_showing_its_partition(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    maritime = await stream_router.stream(user, claims, container, categories="maritime")
    unrelated = await stream_router.stream(user, claims, container, categories="disaster,cyber")
    iterators = [maritime.body_iterator, unrelated.body_iterator]
    try:
        for iterator in iterators:
            assert (await anext(iterator))["event"] == "hello"
        vessels = [
            make_event(f"v{i}", source_id="aisstream", category=Category.MARITIME)
            for i in range(MAX_UPSERT_EVENTS + 1)
        ]
        await container.bus.publish(
            BusMessage("event.upsert", {"source_id": "aisstream", "events": vessels})
        )
        await container.bus.publish(BusMessage("event.expire", {"ids": []}))
        async with asyncio.timeout(2):
            hint = await anext(iterators[0])
            assert (await anext(iterators[0]))["event"] == "event.expire"
            # The unrelated stream skips the hint and receives the next public message.
            assert (await anext(iterators[1]))["event"] == "event.expire"
        assert hint["event"] == "event.resync"
        assert json.loads(hint["data"]) == {
            "reason": "snapshot_required",
            "categories": ["maritime"],
            "source_id": "aisstream",
        }
    finally:
        for iterator in iterators:
            await iterator.aclose()
