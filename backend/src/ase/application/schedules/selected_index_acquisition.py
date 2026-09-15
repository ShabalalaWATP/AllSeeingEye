"""Independent, bounded acquisition of selected public metadata from existing caches."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ase.application.ports import Clock
from ase.application.ports.source_controls import SourceAdmission
from ase.application.schedules.report_request import LOOKBACK_DAYS
from ase.application.schedules.selected_index_types import (
    CacheUnavailable,
    IndexCursor,
    IndexedPage,
    IndexedPageSource,
    IndexedSourcePolicy,
    SelectedIndexAcquisitionStore,
)
from ase.domain.schedules import Schedule

ACTIVE_SCAN = 16
MAX_OPERATIONS_PER_TICK = 2
PAGE_LIMIT = 100
log = logging.getLogger(__name__)


def _progress(since: datetime, after: str) -> str:
    value = f"{since.astimezone(UTC).isoformat()};{after}"
    if len(value) > 512:
        raise ValueError("Selected-index page cursor exceeds its limit")
    return value


def _resume(value: str) -> tuple[datetime, str]:
    try:
        since_text, after = value.split(";", 1)
        since = datetime.fromisoformat(since_text)
        if since.tzinfo is None or not after or len(after) > 400:
            raise ValueError("Invalid page cursor")
        return since.astimezone(UTC), after
    except (TypeError, ValueError) as exc:
        raise CacheUnavailable("Unusable saved page cursor") from exc


def _page_key(
    schedule: Schedule,
    policy: IndexedSourcePolicy,
    until: datetime,
    after: str | None,
    page: IndexedPage,
) -> str:
    value = [
        str(schedule.id),
        policy.source_id,
        until.isoformat(),
        after,
        page.next_after,
        [record.fingerprint for record in page.records],
    ]
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _eligible(schedule: Schedule, policy: IndexedSourcePolicy) -> bool:
    """The fixed cache source has no private terms; only an exact selected AOI qualifies."""

    return schedule.research_area is not None and (
        schedule.research_source_ids is None or policy.capability_id in schedule.research_source_ids
    )


def _window(
    now: datetime, cursor: IndexCursor | None, policy: IndexedSourcePolicy
) -> tuple[datetime, datetime, str | None]:
    if cursor is not None and cursor.cursor_value is not None:
        if cursor.watermark_at is None:
            raise CacheUnavailable("Saved page has no cycle watermark")
        since, after = _resume(cursor.cursor_value)
        return since, cursor.watermark_at, after
    earliest_cache = now - policy.cache_history
    since = (
        max(cursor.watermark_at - policy.overlap, earliest_cache)
        if cursor is not None and cursor.watermark_at is not None
        else earliest_cache
    )
    return since, now, None


def _requested_start(schedule: Schedule, now: datetime) -> datetime:
    hours = schedule.window_hours or LOOKBACK_DAYS.get(schedule.cadence, 1) * 24
    return now - timedelta(hours=hours)


class SelectedIndexAcquisition:
    """One page per selected source operation, at most two operations per tick."""

    def __init__(
        self,
        store: SelectedIndexAcquisitionStore,
        sources: tuple[tuple[IndexedSourcePolicy, IndexedPageSource], ...],
        admission: SourceAdmission,
        clock: Clock,
    ) -> None:
        if (
            not sources
            or len(sources) > 32
            or len({policy.source_id for policy, _ in sources}) != len(sources)
        ):
            raise ValueError("Choose one to 32 distinct reviewed selected-index sources")
        self.store, self.sources, self.admission, self.clock = store, sources, admission, clock
        self._after: UUID | None = None
        self._tick_lock = asyncio.Lock()

    async def tick(self) -> int:
        if self._tick_lock.locked():
            return 0
        async with self._tick_lock:
            active = await self.store.active_batch(self._after, ACTIVE_SCAN)
            if not active:
                self._after = None
                return 0
            used = 0
            for candidate in active:
                self._after = candidate.id
                schedule = await self.store.current(candidate.id)
                if schedule is None or not schedule.enabled:
                    continue
                for policy, source in self.sources:
                    if not _eligible(schedule, policy):
                        continue
                    cursor = await self.store.cursor(schedule, policy.source_id)
                    if (
                        cursor is not None
                        and cursor.cursor_value is None
                        and self.clock.now() - cursor.updated_at < policy.minimum_interval
                    ):
                        continue
                    try:
                        await self._acquire(schedule, policy, source, cursor)
                    except Exception:
                        # The exception may contain upstream text, query terms or an AOI.
                        log.warning("selected_index_acquisition_failed")
                    used += 1
                    if used >= MAX_OPERATIONS_PER_TICK:
                        return used
            return used

    async def _gap(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        reason: str,
        start: datetime,
        end: datetime,
    ) -> None:
        if start < end:
            await self.store.record_gap(
                schedule,
                policy.source_id,
                reason=reason,
                start=start,
                end=end,
                now=self.clock.now(),
            )

    async def _acquire(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        source: IndexedPageSource,
        cursor: IndexCursor | None,
    ) -> None:
        now = self.clock.now()
        try:
            since, until, after = _window(now, cursor, policy)
        except CacheUnavailable:
            await self._gap(schedule, policy, "source_outage", now - policy.cache_history, now)
            if cursor is not None:
                empty = IndexedPage((), None)
                async with self.admission.guard():
                    if await self.admission.enabled(policy.source_id):
                        await self.store.persist(
                            schedule,
                            policy,
                            expected_revision=cursor.revision,
                            page_key=_page_key(schedule, policy, now, cursor.cursor_value, empty),
                            page=empty,
                            cursor_value=None,
                            watermark_at=now,
                            now=now,
                        )
            return
        if cursor is not None and cursor.watermark_at is not None and cursor.watermark_at < since:
            await self._gap(schedule, policy, "source_outage", cursor.watermark_at, since)
        if after is not None and since < now - policy.cache_history:
            # A partly processed cache snapshot vanished during a long interruption.
            # Mark the loss, then reset the page cursor in a short fenced transaction.
            await self._gap(schedule, policy, "source_outage", since, now - policy.cache_history)
            empty = IndexedPage((), None)
            async with self.admission.guard():
                if await self.admission.enabled(policy.source_id):
                    await self.store.persist(
                        schedule,
                        policy,
                        expected_revision=cursor.revision if cursor else 0,
                        page_key=_page_key(schedule, policy, now, after, empty),
                        page=empty,
                        cursor_value=None,
                        watermark_at=now,
                        now=self.clock.now(),
                    )
            return
        requested_start = _requested_start(schedule, now)
        if cursor is None and requested_start < since:
            await self._gap(schedule, policy, "initial_history_gap", requested_start, since)
        retention_start = now - timedelta(days=policy.retention_days)
        if requested_start < retention_start:
            await self._gap(schedule, policy, "retention_horizon", requested_start, retention_start)
        if not await self.admission.enabled(policy.source_id):
            await self._gap(schedule, policy, "source_disabled", since, until)
            return
        try:
            page = await source.fetch_page(
                schedule, policy, since=since, until=until, after=after, limit=PAGE_LIMIT
            )
        except Exception:
            # Upstream/cache exceptions can embed a URL, private area or credentials.
            await self._gap(schedule, policy, "source_outage", since, until)
            return
        if page.truncated or len(page.records) > PAGE_LIMIT:
            await self._gap(schedule, policy, "cache_truncated", since, until)
            return
        progress = _progress(since, page.next_after) if page.next_after is not None else None
        async with self.admission.guard():
            if not await self.admission.enabled(policy.source_id):
                await self._gap(schedule, policy, "source_disabled", since, until)
                return
            await self.store.persist(
                schedule,
                policy,
                expected_revision=cursor.revision if cursor else 0,
                page_key=_page_key(schedule, policy, until, after, page),
                page=page,
                cursor_value=progress,
                watermark_at=until,
                now=self.clock.now(),
            )
