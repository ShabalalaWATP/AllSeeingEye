"""Fresh subscription scope and gap/page commits on disposable SQLite."""

from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.selected_index_acquisition import SqlSelectedIndexAcquisitionStore
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.adapters.research.selected_event_cache import USGS_SELECTED_POLICY, PublicEventCachePages
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry
from ase.application.schedules.selected_index_acquisition import SelectedIndexAcquisition
from ase.application.schedules.selected_index_types import IndexedPage
from ase.domain.events import Category, Event, GeoConfidence, Point, Reliability
from ase.domain.research_area import area_to_dict
from test_selected_index_acquisition import AREA, NOW, POLICY, Admission, Clock, _record
from test_selected_subscription_index import _database, _schedule


class _Access:
    async def background(self, owner_id, team_id, *, for_update=False):
        return SimpleNamespace(actor=SimpleNamespace(id=owner_id), memberships={})


@pytest.mark.asyncio
async def test_page_and_outage_use_current_enabled_scope() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            row = _schedule(subscription_id, owner)
            row.research_options = {
                "research_area": area_to_dict(AREA),
                "source_ids": [POLICY.capability_id],
            }
            session.add(row)
        store = SqlSelectedIndexAcquisitionStore(maker, lambda session: _Access())
        (schedule,) = await store.active_batch(None, 16)
        assert schedule.id == subscription_id
        assert await store.current(subscription_id) == schedule
        assert await store.cursor(schedule, POLICY.source_id) is None
        await store.record_gap(
            schedule,
            POLICY.source_id,
            reason="initial_history_gap",
            start=NOW - timedelta(days=366),
            end=NOW - timedelta(days=1),
            now=NOW,
        )
        assert await store.persist(
            schedule,
            POLICY,
            expected_revision=0,
            page_key="first",
            page=IndexedPage((_record("a"),), None),
            cursor_value=None,
            watermark_at=NOW,
            now=NOW,
        )
        assert (await store.cursor(schedule, POLICY.source_id)).revision == 1
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            losses = await repo.list_losses(subscription_id, actor_id=owner)
            assert len(losses) == 1 and losses[0].reason == "initial_history_gap"
            assert len(await repo.list_records(subscription_id, actor_id=owner)) == 1
        async with maker.begin() as session:
            row = await session.get(ScheduleRow, subscription_id)
            assert row is not None
            row.enabled = False
        assert await store.current(subscription_id) is None
        assert not await store.persist(
            schedule,
            POLICY,
            expected_revision=1,
            page_key="second",
            page=IndexedPage((_record("b"),), None),
            cursor_value=None,
            watermark_at=NOW + timedelta(hours=1),
            now=NOW + timedelta(hours=1),
        )
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            cursor = await repo.get_cursor(subscription_id, POLICY.source_id, actor_id=owner)
            assert cursor is not None and cursor.revision == 1
            assert len(await repo.list_records(subscription_id, actor_id=owner)) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_public_cache_flows_to_scoped_index_without_provider_call() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            row = _schedule(subscription_id, owner)
            row.research_options = {
                "research_area": area_to_dict(AREA),
                "source_ids": [USGS_SELECTED_POLICY.capability_id],
            }
            session.add(row)
        cache, health = InMemoryEventStore(), HealthRegistry()
        cache.upsert(
            (
                Event(
                    id="usgsitem",
                    source_id=USGS_SELECTED_POLICY.source_id,
                    category=Category.DISASTER,
                    subtype="earthquake",
                    title="Public quake",
                    published_at=NOW - timedelta(hours=1),
                    observed_at=NOW,
                    reliability=Reliability.A,
                    point=Point(0.5, 50.5),
                    geo_confidence=GeoConfidence.EXACT,
                    content_hash="a" * 64,
                ),
            )
        )
        health.record_success(USGS_SELECTED_POLICY.source_id, 1, 1.0, NOW, timedelta(minutes=5))
        collector = SelectedIndexAcquisition(
            SqlSelectedIndexAcquisitionStore(maker, lambda session: _Access()),
            ((USGS_SELECTED_POLICY, PublicEventCachePages(cache, health)),),
            Admission(),
            Clock(),
        )
        assert await collector.tick() == 1
        async with maker() as session:
            rows = await SqlSelectedSubscriptionIndexRepository(session).list_records(
                subscription_id, actor_id=owner
            )
            assert len(rows) == 1
            assert rows[0].item_key == "usgsitem"
            assert rows[0].policy_id == USGS_SELECTED_POLICY.policy_id
    finally:
        await engine.dispose()
