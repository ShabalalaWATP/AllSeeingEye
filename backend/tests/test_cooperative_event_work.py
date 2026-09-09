"""Large event work yields without changing retained data or worker admission."""

import asyncio
import threading
from datetime import timedelta
from unittest.mock import Mock

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.firms import SPEC
from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import EventQuery
from ase.domain.errors import RateLimited
from feeds_helpers import NOW, FakeClock, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_cooperative_upsert_matches_atomic_retention_and_yields():
    rows = [make_event(str(i)) for i in range(1000)]
    budget = estimate_bytes(rows[0]) * 600
    sync = InMemoryEventStore(memory_budget_bytes=budget)
    cooperative = InMemoryEventStore(memory_budget_bytes=budget)
    expected = sync.upsert(rows)
    task = asyncio.create_task(cooperative.upsert_cooperatively(rows))
    await asyncio.sleep(0)
    assert not task.done()
    assert await task == expected
    assert cooperative.query(EventQuery(limit=2000)) == sync.query(EventQuery(limit=2000))
    assert cooperative.prune(NOW) == sync.prune(NOW)


async def test_cancelled_upsert_enforces_budget_and_stats_cache_invalidates():
    row = make_event()
    store = InMemoryEventStore(memory_budget_bytes=estimate_bytes(row) * 10)
    original = store.stats()
    assert store.stats() is original
    task = asyncio.create_task(
        store.upsert_cooperatively([make_event(str(i)) for i in range(1000)])
    )
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert store.stats().estimated_bytes <= store.stats().budget_bytes
    assert store.stats() is not original


async def test_cooperative_grading_matches_sync_and_does_not_resurrect_stale_versions():
    rows = [make_event(str(i), source_id=SPEC.id) for i in range(600)]
    sync, store = InMemoryEventStore(), InMemoryEventStore()
    sync.upsert(rows)
    store.upsert(rows)
    profiles = profiles_from_specs([SPEC])
    expected = GradingService(sync, profiles, FakeClock(NOW)).regrade(rows)
    result = await GradingService(store, profiles, FakeClock(NOW)).regrade_cooperatively(rows)
    assert result == expected
    assert store.query(EventQuery(limit=1000)) == sync.query(EventQuery(limit=1000))
    newer = make_event("0", source_id=SPEC.id, version=2)
    store.upsert([newer])
    await store.put_grades_cooperatively([rows[0], make_event("never-stored")])
    assert store.get(newer.id) == newer
    assert store.get(make_event("never-stored").id) is None


async def test_query_worker_uses_snapshot_and_cancel_does_not_release_running_slot():
    store = InMemoryEventStore()
    old = make_event()
    store.upsert([old])
    entered, release = threading.Event(), threading.Event()

    def project(rows):
        entered.set()
        assert release.wait(3)
        return rows

    first = asyncio.create_task(store.read_cooperatively(EventQuery(), project))
    while not entered.is_set():
        await asyncio.sleep(0)
    store.upsert([make_event(version=2)])
    first.cancel()
    second_project = Mock(side_effect=lambda rows: rows)
    second = asyncio.create_task(store.read_cooperatively(EventQuery(), second_project))
    await asyncio.sleep(0)
    first.cancel()  # Repeated cancellation cannot admit a second CPU worker.
    await asyncio.sleep(0)
    second_project.assert_not_called()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert (await second)[0].content_hash != old.content_hash
    assert store._waiting_reads == 0


async def test_worker_queue_is_bounded_and_result_matches_geographic_query():
    store = InMemoryEventStore()
    store.upsert([make_event(str(i)) for i in range(20)])
    query = EventQuery(sampling="geographic", limit=7)
    assert await store.read_cooperatively(query, lambda rows: rows) == store.query(query)
    store._waiting_reads = 8
    with pytest.raises(RateLimited):
        await store.read_cooperatively(query, lambda rows: rows)


async def test_events_rechecks_revocation_after_worker_yields(client, container, user, monkeypatch):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)

    async def interrupted_read(query, project):
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return project([make_event()])

    monkeypatch.setattr(container.store, "read_cooperatively", interrupted_read)
    response = await client.get("/api/events", headers=bearer(token))
    assert response.status_code == 401
    assert "Test event" not in response.text


async def test_scheduler_does_not_publish_observation_pruned_during_grading():
    store = InMemoryEventStore()
    event = make_event()
    store.upsert([event])

    class PruningGrader:
        def regrade(self, events):
            raise AssertionError("cooperative path expected")

        async def regrade_cooperatively(self, events):
            store.prune(NOW + timedelta(days=30))
            return list(events)

    scheduler = FeedScheduler(
        [],
        Pipeline([]),
        store,
        InMemoryEventBus(),
        HealthRegistry(),
        FakeClock(NOW),
        grader=PruningGrader(),
    )
    assert await scheduler._regraded([event]) == []
