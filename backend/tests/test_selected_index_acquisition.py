"""Independent selected-source acquisition with offline pages and durable cursor fakes."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from ase.application.schedules.runner import ScheduleRunner
from ase.application.schedules.selected_index_acquisition import SelectedIndexAcquisition
from ase.application.schedules.selected_index_types import (
    IndexCursor,
    IndexedPage,
    IndexedSourcePolicy,
)
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.schedules import Schedule
from ase.domain.selected_subscription_index import SelectedMetadata

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)
POLICY = IndexedSourcePolicy(
    source_id="usgs_earthquakes",
    capability_id="research-usgs-area",
    policy_id="usgs-authored-metadata-v1",
    retention_days=30,
    minimum_interval=timedelta(hours=1),
    overlap=timedelta(hours=36),
    cache_history=timedelta(days=1),
    max_cache_age=timedelta(minutes=30),
)
AREA = direct_area_from_geometry(
    {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                },
            }
        ],
    }
)


def _schedule(*, cadence: str = "daily") -> Schedule:
    return Schedule(
        id=uuid4(),
        name="Selected",
        template_id="intsum",
        country_iso=None,
        plan_id=None,
        hour_utc=6,
        cadence=cadence,
        weekday=0,
        window_hours=None,
        enabled=True,
        created_by=uuid4(),
        created_at=NOW,
        next_run_at=NOW + timedelta(days=1),
        research_area=AREA,
        research_source_ids=(POLICY.capability_id,),
    )


def _record(key: str) -> SelectedMetadata:
    return SelectedMetadata(
        source_id=POLICY.source_id,
        item_key=key,
        origin_key=key,
        source_version="event-v1",
        title=f"Event {key}",
        content_sha256="a" * 64,
        policy_id=POLICY.policy_id,
        retention_days=POLICY.retention_days,
        retrieved_at=NOW,
        observed_at=NOW,
        published_at=NOW - timedelta(hours=1),
    )


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def now(self) -> datetime:
        return self.value


class Admission:
    def __init__(self) -> None:
        self.is_enabled = True

    async def enabled(self, source_id: str) -> bool:
        assert source_id == POLICY.source_id
        return self.is_enabled

    @asynccontextmanager
    async def guard(self):
        yield


class Store:
    def __init__(self, schedules: tuple[Schedule, ...]) -> None:
        self.schedules = {schedule.id: schedule for schedule in schedules}
        self.cursors: dict[tuple[UUID, str], IndexCursor] = {}
        self.records: list[SelectedMetadata] = []
        self.gaps: list[tuple[str, datetime, datetime]] = []

    async def active_batch(self, after: UUID | None, limit: int) -> tuple[Schedule, ...]:
        return tuple(
            self.schedules[key] for key in sorted(self.schedules) if after is None or key > after
        )[:limit]

    async def current(self, subscription_id: UUID) -> Schedule | None:
        schedule = self.schedules.get(subscription_id)
        return schedule if schedule is not None and schedule.enabled else None

    async def cursor(self, schedule: Schedule, source_id: str) -> IndexCursor | None:
        return self.cursors.get((schedule.id, source_id))

    async def persist(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        *,
        expected_revision: int,
        page_key: str,
        page: IndexedPage,
        cursor_value: str | None,
        watermark_at: datetime,
        now: datetime,
    ) -> bool:
        assert page_key and self.schedules[schedule.id].enabled
        prior = self.cursors.get((schedule.id, policy.source_id))
        assert expected_revision == (prior.revision if prior else 0)
        self.records.extend(page.records)
        self.cursors[(schedule.id, policy.source_id)] = IndexCursor(
            expected_revision + 1, cursor_value, watermark_at, now
        )
        return True

    async def record_gap(
        self,
        schedule: Schedule,
        source_id: str,
        *,
        reason: str,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> None:
        assert source_id == POLICY.source_id and now >= end
        self.gaps.append((reason, start, end))


class Pages:
    def __init__(self, pages: tuple[IndexedPage, ...], admission: Admission | None = None) -> None:
        self.pages = list(pages)
        self.calls: list[tuple[datetime, datetime, str | None]] = []
        self.admission = admission

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
        assert policy == POLICY and schedule.research_area == AREA and limit == 100
        self.calls.append((since, until, after))
        if self.admission is not None:
            self.admission.is_enabled = False
        return self.pages.pop(0)


@pytest.mark.asyncio
async def test_restart_mid_page_resumes_exact_cursor_then_respects_hourly_cadence() -> None:
    schedule = _schedule()
    store, admission, clock = Store((schedule,)), Admission(), Clock()
    pages = Pages((IndexedPage((_record("a"),), "key-a"), IndexedPage((_record("b"),), None)))
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    saved = store.cursors[(schedule.id, POLICY.source_id)]
    assert saved.revision == 1 and saved.cursor_value is not None
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    assert pages.calls[1][0] == pages.calls[0][0]
    assert pages.calls[1][1] == pages.calls[0][1]
    assert pages.calls[1][2] == "key-a"
    assert store.cursors[(schedule.id, POLICY.source_id)].cursor_value is None
    assert [record.item_key for record in store.records] == ["a", "b"]
    clock.value += timedelta(minutes=30)
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 0


@pytest.mark.asyncio
async def test_source_disabled_during_cache_read_never_persists_page() -> None:
    schedule = _schedule()
    store, admission, clock = Store((schedule,)), Admission(), Clock()
    pages = Pages((IndexedPage((_record("a"),), None),), admission)
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    assert store.records == [] and store.cursors == {}
    assert any(reason == "source_disabled" for reason, _, _ in store.gaps)
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    assert len(pages.calls) == 1


@pytest.mark.asyncio
async def test_annual_window_records_unavailable_history_and_retention_gap() -> None:
    schedule = _schedule(cadence="annual")
    store, admission, clock = Store((schedule,)), Admission(), Clock()
    pages = Pages((IndexedPage((), None),))
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    by_reason = {reason: (start, end) for reason, start, end in store.gaps}
    assert by_reason["initial_history_gap"][0] <= NOW - timedelta(days=365)
    assert by_reason["initial_history_gap"][1] == NOW - POLICY.cache_history
    assert by_reason["retention_horizon"][1] == NOW - timedelta(days=30)


@pytest.mark.asyncio
async def test_restart_after_cache_expiry_records_outage_and_resets_page_cursor() -> None:
    schedule = _schedule()
    store, admission, clock = Store((schedule,)), Admission(), Clock()
    old = NOW - timedelta(days=3)
    store.cursors[(schedule.id, POLICY.source_id)] = IndexCursor(
        1, f"{old.isoformat()};old-key", old, old
    )
    pages = Pages(())
    assert await SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock).tick() == 1
    assert pages.calls == []
    cursor = store.cursors[(schedule.id, POLICY.source_id)]
    assert cursor.revision == 2 and cursor.cursor_value is None
    assert any(reason == "source_outage" for reason, _, _ in store.gaps)


@pytest.mark.asyncio
async def test_acquisition_uses_at_most_two_source_operations_per_tick() -> None:
    schedules = tuple(_schedule() for _ in range(3))
    store, admission, clock = Store(schedules), Admission(), Clock()
    pages = Pages(tuple(IndexedPage((), None) for _ in schedules))
    collector = SelectedIndexAcquisition(store, ((POLICY, pages),), admission, clock)
    assert await collector.tick() == 2
    assert len(pages.calls) == 2
    assert await collector.tick() == 1
    assert len(pages.calls) == 3


@pytest.mark.asyncio
async def test_runner_acquisition_loop_is_independent_of_blocked_publication() -> None:
    entered, acquired = asyncio.Event(), asyncio.Event()

    async def enqueue() -> int:
        entered.set()
        await asyncio.Event().wait()
        return 0

    async def acquire() -> int:
        acquired.set()
        return 1

    runner = ScheduleRunner(enqueue, acquisition_tick=acquire, interval=timedelta(hours=1))
    await runner.start()
    try:
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(acquired.wait(), 1)
    finally:
        await runner.stop()
