"""Reviewed USGS metadata reads from the existing public cache, without network calls."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research.selected_event_cache import USGS_SELECTED_POLICY, PublicEventCachePages
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry
from ase.application.schedules.selected_index_types import CacheUnavailable
from ase.domain.events import Category, Event, GeoConfidence, Point, Reliability
from test_selected_index_acquisition import NOW, _schedule


def _event(key: str, *, lon: float = 0.5, title: str = "Public event") -> Event:
    return Event(
        id=key,
        source_id="usgs_earthquakes",
        category=Category.DISASTER,
        subtype="earthquake",
        title=title,
        published_at=NOW - timedelta(hours=1),
        observed_at=NOW - timedelta(minutes=2),
        reliability=Reliability.A,
        point=Point(lon, 50.5),
        geo_confidence=GeoConfidence.EXACT,
        country_iso="GB",
        content_hash="a" * 64,
    )


@pytest.mark.asyncio
async def test_cache_page_has_exact_area_and_no_private_question_key() -> None:
    store, health = InMemoryEventStore(), HealthRegistry()
    store.upsert((_event("inside"), _event("outside", lon=1.5)))
    health.record_success(USGS_SELECTED_POLICY.source_id, 2, 1.0, NOW, timedelta(minutes=5))
    source = PublicEventCachePages(store, health)
    schedule = replace(_schedule(), question="private merger question")
    page = await source.fetch_page(
        schedule,
        USGS_SELECTED_POLICY,
        since=NOW - timedelta(days=1),
        until=NOW,
        after=None,
        limit=100,
    )
    assert [record.item_key for record in page.records] == ["inside"]
    assert page.records[0].title == "Public event"
    assert not hasattr(page.records[0], "summary")
    assert page.next_after is None
    other = await source.fetch_page(
        replace(schedule, question="a different private term"),
        USGS_SELECTED_POLICY,
        since=NOW - timedelta(days=1),
        until=NOW,
        after=None,
        limit=100,
    )
    assert other == page


@pytest.mark.asyncio
async def test_stale_cache_or_unreviewed_policy_fails_closed() -> None:
    store, health = InMemoryEventStore(), HealthRegistry()
    source = PublicEventCachePages(store, health)
    with pytest.raises(CacheUnavailable):
        await source.fetch_page(
            _schedule(),
            USGS_SELECTED_POLICY,
            since=NOW - timedelta(days=1),
            until=NOW,
            after=None,
            limit=100,
        )
    health.record_success(USGS_SELECTED_POLICY.source_id, 0, 1.0, NOW, timedelta(minutes=5))
    with pytest.raises(CacheUnavailable, match="terms"):
        await source.fetch_page(
            _schedule(),
            replace(USGS_SELECTED_POLICY, policy_id="unreviewed"),
            since=NOW - timedelta(days=1),
            until=NOW,
            after=None,
            limit=100,
        )
