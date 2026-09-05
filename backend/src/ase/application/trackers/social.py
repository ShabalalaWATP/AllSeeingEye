"""Social board and sampler, computed from the bounded live store."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.social import SocialActivityStore, SocialTermsSource
from ase.domain.events import Category, Event
from ase.domain.social import (
    HashtagActivity,
    KeywordActivity,
    PlatformActivity,
    keyword_counts,
    platform_groups,
    top_hashtags,
)
from ase.domain.users import User

log = logging.getLogger(__name__)
BASELINE_DAYS = 30
SOCIAL_POOL = 20_000
SAMPLE_INTERVAL = timedelta(minutes=5)
SleepFn = Callable[[float], Awaitable[None]]


def social_events(store: EventStore, since: datetime, before: datetime) -> list[Event]:
    return [
        event
        for event in store.query(
            EventQuery(categories=frozenset({Category.SOCIAL}), since=since, limit=SOCIAL_POOL)
        )
        if since <= event.published_at < before
    ]


@dataclass(frozen=True, slots=True)
class SocialBoard:
    total: int
    located: int
    platforms: tuple[PlatformActivity, ...]
    hashtags: tuple[HashtagActivity, ...]
    keywords: tuple[KeywordActivity, ...]
    posts: tuple[Event, ...]
    window_start: datetime
    window_end: datetime
    keyword_hour: datetime


class SocialService:
    def __init__(
        self,
        store: EventStore,
        terms: SocialTermsSource,
        activity: SocialActivityStore,
        clock: Clock,
    ) -> None:
        self._store = store
        self._terms = terms
        self._activity = activity
        self._clock = clock

    async def board(self, actor: User) -> SocialBoard:
        now = self._clock.now()
        hour_end = now.replace(minute=0, second=0, microsecond=0)
        hour = hour_end - timedelta(hours=1)
        since = now - timedelta(hours=24)
        events = social_events(self._store, since, now)
        terms = tuple(
            term
            for term in await self._terms.configured()
            if term.public or actor.is_admin or actor.id in term.owners
        )
        counts = keyword_counts(
            [event for event in events if hour <= event.published_at < hour_end], terms
        )
        baselines = await self._activity.baselines(
            hour_end - timedelta(days=BASELINE_DAYS), hour, [term.key for term in terms]
        )
        keywords = []
        for term in terms:
            baseline = baselines.get(term.key)
            keywords.append(
                KeywordActivity(
                    term.term,
                    counts[term.key],
                    baseline.mean if baseline else None,
                    baseline.hours if baseline else 0,
                )
            )
        keywords.sort(key=lambda row: (not row.burst, -row.count, row.term))
        return SocialBoard(
            total=len(events),
            located=sum(event.point is not None for event in events),
            platforms=platform_groups(events),
            hashtags=top_hashtags(events),
            keywords=tuple(keywords),
            posts=tuple(
                sorted(events, key=lambda event: (event.published_at, event.id), reverse=True)[:50]
            ),
            window_start=since,
            window_end=now,
            keyword_hour=hour,
        )


class SocialMonitor:
    """Sample the previous complete UTC hour, including configured terms with zero posts.

    Comparing complete hours avoids treating a partly elapsed hour as a quiet period.
    Repeated samples incorporate late feed arrivals; gaps while stopped stay unknown.
    """

    def __init__(
        self,
        store: EventStore,
        terms: SocialTermsSource,
        activity: SocialActivityStore,
        clock: Clock,
        *,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._store = store
        self._terms = terms
        self._activity = activity
        self._clock = clock
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None

    async def sample(self) -> int:
        end = self._clock.now().replace(minute=0, second=0, microsecond=0)
        hour = end - timedelta(hours=1)
        terms = await self._terms.configured()
        events = social_events(self._store, hour, end)
        await self._activity.record(hour, keyword_counts(events, terms))
        return len(events)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="social-monitor")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.sample()
            except Exception:
                log.warning("Social activity sampling failed")
            await self._sleep(SAMPLE_INTERVAL.total_seconds())
