"""Metadata-only pages from the existing fixed public event-feed cache."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from ase.adapters.research.retained_area_selection import AreaPointFilter
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.schedules.selected_index_types import (
    CacheUnavailable,
    IndexedPage,
    IndexedSourcePolicy,
)
from ase.domain.events import Event, content_hash
from ase.domain.schedules import Schedule
from ase.domain.selected_subscription_index import SelectedMetadata

MAX_CACHE_SCAN = 2_000
_HASH = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")

USGS_SELECTED_POLICY = IndexedSourcePolicy(
    source_id="usgs_earthquakes",
    capability_id="research-usgs-area",
    policy_id="usgs-authored-metadata-v1",
    retention_days=400,
    minimum_interval=timedelta(hours=1),
    overlap=timedelta(hours=36),
    cache_history=timedelta(days=1),
    max_cache_age=timedelta(minutes=30),
)


def _event_key(event: Event) -> str:
    if event.published_at is None or event.published_at.tzinfo is None:
        raise CacheUnavailable("Cached event has no usable publication timestamp")
    return f"{event.published_at.astimezone(UTC).isoformat()}|{event.id}"


def _metadata(event: Event, policy: IndexedSourcePolicy) -> SelectedMetadata:
    version = event.attributes.get("source_version")
    source_version = (
        version if isinstance(version, str) and _VERSION.fullmatch(version) else "event-v1"
    )
    digest = (
        event.content_hash
        if _HASH.fullmatch(event.content_hash)
        else content_hash(event.id, event.title, event.url)
    )
    return SelectedMetadata(
        source_id=policy.source_id,
        item_key=event.id,
        origin_key=event.id,
        source_version=source_version,
        title=event.title,
        content_sha256=digest,
        policy_id=policy.policy_id,
        retention_days=policy.retention_days,
        retrieved_at=event.observed_at,
        published_at=event.published_at,
        observed_at=event.observed_at,
    )


class PublicEventCachePages:
    """Read already-polled public events; never pass a subscription query to the cache."""

    def __init__(self, store: EventStore, health: HealthRegistry) -> None:
        self.store, self.health = store, health

    async def fetch_page(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        *,
        since: datetime,
        until: datetime,
        after: str | None,
        limit: int,
    ) -> IndexedPage:
        if policy != USGS_SELECTED_POLICY:
            raise CacheUnavailable("Source metadata terms are not reviewed for this adapter")
        if schedule.research_area is None or not 1 <= limit <= 100:
            raise CacheUnavailable("Selected cache page lacks an exact area or bounded limit")
        health = self.health.get(policy.source_id)
        if (
            health.status is not SourceStatus.HEALTHY
            or health.last_success is None
            or health.last_success.tzinfo is None
            or until - health.last_success > policy.max_cache_age
        ):
            raise CacheUnavailable("Selected public feed cache is not healthy and fresh")
        spatial = AreaPointFilter(schedule.research_area)
        candidates = self.store.query(
            EventQuery(
                source_ids=frozenset({policy.source_id}),
                bbox=spatial.bounds,
                since=since,
                until=until,
                limit=MAX_CACHE_SCAN + 1,
            )
        )
        if len(candidates) > MAX_CACHE_SCAN:
            return IndexedPage((), None, truncated=True)
        matched = sorted(
            (
                event
                for event in candidates
                if spatial.contains(event)
                and (not schedule.country_isos or event.country_iso in schedule.country_isos)
            ),
            key=_event_key,
        )
        if after is not None:
            matched = [event for event in matched if _event_key(event) > after]
        page = matched[:limit]
        next_after = _event_key(page[-1]) if len(matched) > limit and page else None
        return IndexedPage(tuple(_metadata(event, policy) for event in page), next_after)
