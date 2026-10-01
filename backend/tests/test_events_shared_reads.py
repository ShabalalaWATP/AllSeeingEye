"""Identical concurrent `/api/events` reads share one selection and response build."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from ase.adapters.store.memory import InMemoryEventStore
from ase.api import shared_event_reads
from ase.api.schemas_events import EventOut
from ase.container import Container
from ase.domain.events import Category
from feeds_helpers import NOW, make_event
from helpers import USER_PASSWORD, bearer, create_user, login_token


async def tokens(client: AsyncClient, container: Container, count: int) -> list[str]:
    result = []
    for index in range(count):
        email = f"reader{index}@example.com"
        await create_user(container, email=email, password=USER_PASSWORD)
        result.append(await login_token(client, email, USER_PASSWORD))
    return result


def count_builds(monkeypatch: pytest.MonkeyPatch, store: InMemoryEventStore) -> dict[str, int]:
    counts = {"selections": 0, "dtos": 0}
    select = store.read_cooperatively
    build = EventOut.from_event

    async def counted_read(query: Any, project: Callable[[Any], Any], **options: Any) -> Any:
        counts["selections"] += 1
        await asyncio.sleep(0.05)  # Hold the read open so the other requests overlap it.
        return await select(query, project, **options)

    def counted_build(event: Any) -> EventOut:
        counts["dtos"] += 1
        return build(event)

    monkeypatch.setattr(store, "read_cooperatively", counted_read)
    monkeypatch.setattr(EventOut, "from_event", counted_build)
    return counts


async def test_ten_identical_simultaneous_queries_share_one_build(
    client: AsyncClient, container: Container, monkeypatch: pytest.MonkeyPatch
) -> None:
    container.store.upsert([make_event("a"), make_event("b", category=Category.MARITIME)])
    readers = await tokens(client, container, 10)
    counts = count_builds(monkeypatch, container.store)
    responses = await asyncio.gather(
        *(client.get("/api/events?limit=50", headers=bearer(token)) for token in readers)
    )
    assert {response.status_code for response in responses} == {200}
    assert len({response.text for response in responses}) == 1
    assert counts == {"selections": 1, "dtos": 2}

    # Another filter is another key; an anonymous caller is still refused.
    maritime = await client.get("/api/events?categories=maritime", headers=bearer(readers[0]))
    assert maritime.json()["count"] == 1 and counts["selections"] == 2
    assert (await client.get("/api/events?limit=50")).status_code == 401


@pytest.mark.parametrize("change", ["upsert", "expire", "regrade"])
async def test_store_changes_invalidate_shared_results(
    client: AsyncClient, container: Container, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    store = container.store
    store.upsert([make_event("a", observed_at=NOW - timedelta(days=60))])
    [token] = await tokens(client, container, 1)
    counts = count_builds(monkeypatch, store)
    first = await client.get("/api/events", headers=bearer(token))
    again = await client.get("/api/events", headers=bearer(token))
    assert first.text == again.text and counts["selections"] == 1
    if change == "upsert":
        store.upsert([make_event("b")])
    elif change == "expire":
        assert store.prune(NOW).expired == 1
    else:
        stored = store.get(make_event("a").id)
        assert stored is not None
        store.put([stored.with_changes(story_id="story-1")])
    changed = await client.get("/api/events", headers=bearer(token))
    assert counts["selections"] == 2
    assert changed.text != first.text


async def test_each_store_keeps_its_own_shared_results() -> None:
    first, second = InMemoryEventStore(), InMemoryEventStore()
    assert shared_event_reads.shared_reads(first) is shared_event_reads.shared_reads(first)
    assert shared_event_reads.shared_reads(first) is not shared_event_reads.shared_reads(second)
