"""Board projections share bounded read admission and retain current authority."""

import asyncio
import threading
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.application.feeds.budgets import RetentionBudget
from ase.application.trackers.modules import ModuleService
from ase.domain.errors import RateLimited
from ase.domain.events import Category
from feeds_helpers import NOW, FakeClock, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_modules import module_events


@pytest.mark.parametrize("method", ["maritime_board", "space_board", "cyber_board"])
async def test_board_matches_pure_helper_and_shares_admission_limit(method):
    store = InMemoryEventStore()
    store.upsert(module_events())
    service = ModuleService(store, FakeClock(NOW))
    result = await service.read(lambda snapshot: getattr(snapshot, method)(), admission_key="one")
    assert result == getattr(service, method)()
    store._waiting_reads = 8
    with pytest.raises(RateLimited):
        await service.read(lambda snapshot: getattr(snapshot, method)(), admission_key="one")


async def test_cancelled_board_keeps_slot_until_snapshot_worker_exits():
    store = InMemoryEventStore()
    original = make_event()
    store.upsert([original])
    entered, release = threading.Event(), threading.Event()

    def blocked(reader):
        entered.set()
        assert release.wait(5)
        return reader

    task = asyncio.create_task(store.read_snapshot_cooperatively(blocked, admission_key="one"))
    try:
        while not entered.is_set():
            await asyncio.sleep(0)
        store.upsert([make_event(version=2)])
        task.cancel()
        await asyncio.sleep(0)
        assert store._waiting_reads == 1 and not task.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert store._waiting_reads == 0


@pytest.mark.parametrize("path", ["/api/trackers/maritime", "/api/conflicts/ukraine"])
async def test_board_rechecks_revocation_after_worker(client, container, user, monkeypatch, path):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    original = container.store.read_snapshot_cooperatively

    async def revoke(project, *, admission_key):
        result = await original(project, admission_key=admission_key)
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return result

    monkeypatch.setattr(container.store, "read_snapshot_cooperatively", revoke)
    assert (await client.get(path, headers=bearer(token))).status_code == 401


async def test_board_rejects_snapshot_if_source_disabled_during_read(
    client, container, user, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    switches = AsyncMock(side_effect=[{"nga_navarea": True}, {"nga_navarea": False}])
    monkeypatch.setattr(container.source_admission, "enabled_many", switches)
    response = await client.get("/api/trackers/maritime", headers=bearer(token))
    assert response.status_code == 429 and response.headers["cache-control"] == "no-store"


async def test_board_rejects_disabled_enabled_disabled_source_during_read(
    client, container, user, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    original = container.store.read_snapshot_cooperatively
    generation = [7]
    monkeypatch.setattr(
        type(container.source_admission), "generation", property(lambda self: generation[0])
    )
    switches = AsyncMock(return_value={"nga_navarea": False})
    monkeypatch.setattr(container.source_admission, "enabled_many", switches)

    async def toggled(project, *, admission_key):
        generation[0] += 1
        result = await original(project, admission_key=admission_key)
        generation[0] += 1
        return result

    monkeypatch.setattr(container.store, "read_snapshot_cooperatively", toggled)
    response = await client.get("/api/trackers/maritime", headers=bearer(token))
    assert response.status_code == 429 and response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("global_budget", [False, True])
def test_equal_time_eviction_is_id_ordered_and_announced_once(global_budget):
    rows = [make_event(str(i), observed_at=NOW) for i in range(4)]
    expected = tuple(sorted(row.id for row in rows)[:2])
    for supplied in (rows, list(reversed(rows))):
        store = InMemoryEventStore(
            budgets={
                Category.DISASTER: RetentionBudget(timedelta(days=7), 4 if global_budget else 2)
            },
            memory_budget_bytes=estimate_bytes(rows[0]) * 2 if global_budget else 100_000,
        )
        store.upsert(supplied)
        result = store.prune(NOW)
        assert result.ids == expected and result.evicted == 2
        assert all(store.get(identifier) is None for identifier in expected)
        assert store.prune(NOW).ids == ()
