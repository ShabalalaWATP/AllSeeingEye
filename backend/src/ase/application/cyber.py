"""Bounded cyber observations and publication counts from admitted retained feeds."""

import asyncio
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlsplit

from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.feeds.health import HealthRegistry
from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.cyber import (
    ACTOR_REFERENCE_SOURCE_ID,
    CyberActorTally,
    CyberDailyCount,
    CyberItem,
    CyberKev,
    CyberKind,
    CyberKindCount,
    CyberSnapshot,
    CyberSource,
    CyberStateTally,
    CyberTally,
    CyberThemeTally,
    CyberWindowDays,
    cyber_kind,
    cyber_window,
)
from ase.domain.cyber_actors import CyberActorReference, match_actor_mentions
from ase.domain.cyber_themes import CyberTheme, classify_cyber_themes
from ase.domain.errors import RateLimited
from ase.domain.events import Category, Event
from ase.domain.sources import SourceSpec

MAX_POOL = 8_000
MAX_ITEMS = 200
MAX_STATE_GROUPS = 12
COVERAGE_NOTE = (
    "Counts describe available records from enabled feeds, not total attacks or victims. "
    "Publisher snapshots and the bounded memory cache may not cover the full selected period. "
    "Zero means no retained records in that bucket, not absence of activity. "
    "Ransomware entries are unverified criminal claims; outage signals do not establish "
    "a cyberattack. KEV dates are catalogue additions, not exploitation onset, and due dates "
    "are CISA remediation deadlines with their stated scope. Country codes preserve source "
    "metadata, not verified attack locations. Actor names are headline mentions, not attribution. "
    "Daily volume uses UTC publication dates, including partial first and last days."
)


@dataclass(frozen=True, slots=True)
class CyberSelection:
    events: tuple[Event, ...]
    items: tuple[CyberItem, ...]
    source_ids: tuple[str, ...]
    as_of: datetime
    days: CyberWindowDays


class CyberService:
    def __init__(
        self,
        store: EventStore,
        clock: Clock,
        sources: Mapping[str, SourceSpec],
        admission: SourceAdmission,
        health: HealthRegistry,
        actors: tuple[CyberActorReference, ...] = (),
    ) -> None:
        self._store, self._clock = store, clock
        self._sources, self._admission, self._health = sources, admission, health
        self._actors = actors
        self._preparation = asyncio.Semaphore(1)

    async def read(self, days: CyberWindowDays = CyberWindowDays.TWO) -> CyberSelection:
        days = cyber_window(days)
        enabled = await self._admission.enabled_many((*self._sources, ACTOR_REFERENCE_SOURCE_ID))
        source_ids = tuple(key for key in self._sources if enabled.get(key, False))
        now = self._clock.now().astimezone(UTC)
        events = (
            self._store.query(
                EventQuery(
                    categories=frozenset({Category.CYBER}),
                    source_ids=frozenset(source_ids),
                    since=now - timedelta(days=days),
                    until=now,
                    limit=MAX_POOL,
                )
            )
            if source_ids
            else []
        )
        # Pure matching may inspect thousands of titles. It runs outside the event
        # loop and source guard, with one bounded worker and no waiting work queue.
        if self._preparation.locked():
            raise RateLimited(1)
        actors = self._actors if enabled.get(ACTOR_REFERENCE_SOURCE_ID, False) else ()
        async with self._preparation:
            items = await joined_thread_call(
                lambda: self._items(events, now - timedelta(days=days), now, actors)
            )
        return CyberSelection(tuple(events), items, source_ids, now, days)

    async def release(self, selected: CyberSelection) -> CyberSnapshot:
        """Caller holds the source guard through response construction. No network work."""
        enabled = await self._admission.enabled_many(
            (*selected.source_ids, ACTOR_REFERENCE_SOURCE_ID)
        )
        actors = self._actors if enabled.get(ACTOR_REFERENCE_SOURCE_ID, False) else ()
        source_ids = tuple(key for key in selected.source_ids if enabled.get(key, False))
        start = selected.as_of - timedelta(days=selected.days)
        states = {
            actor.group_id: actor.state_association for actor in actors if actor.state_association
        }
        rows = [
            _released(row, bool(actors), states)
            for row in selected.items
            if row.source_id in source_ids
        ]
        counts = Counter(item.kind for item in rows)
        countries = Counter(item.country_iso for item in rows if item.country_iso)
        groups = Counter(mention.group_id for row in rows for mention in row.actor_mentions)
        actor_names = {actor.group_id: actor.name for actor in actors}
        source_counts = Counter(row.source_id for row in rows)
        days = _days(start, selected.as_of)
        return CyberSnapshot(
            selected.as_of,
            selected.days,
            start,
            selected.as_of,
            COVERAGE_NOTE,
            len(rows),
            min(MAX_ITEMS, len(rows)),
            len(rows) > MAX_ITEMS,
            _counts(counts),
            _timeline(rows, days),
            tuple(CyberTally(key, count) for key, count in countries.most_common(250)),
            tuple(
                CyberActorTally(key, actor_names[key], count)
                for key, count in groups.most_common(300)
            ),
            tuple(self._source(key, source_counts[key]) for key in source_ids),
            tuple(rows[:MAX_ITEMS]),
            _themes(rows, days),
            _state_mentions(rows, states),
        )

    def _items(
        self,
        events: list[Event],
        start: datetime,
        end: datetime,
        actors: tuple[CyberActorReference, ...],
    ) -> tuple[CyberItem, ...]:
        rows: list[CyberItem] = []
        for event in events:
            if (
                event.published_at is None
                or not start <= event.published_at < end
                or not _safe_link(event.url)
            ):
                continue
            spec = self._sources[event.source_id]
            kind = cyber_kind(event.subtype)
            mentions = match_actor_mentions(event.title, actors)
            summary = event.summary[:2_000] if event.summary else None
            themes = classify_cyber_themes(
                f"{event.title} {summary or ''}",
                source_id=event.source_id,
                country_iso=event.country_iso,
                connectivity_signal=kind is CyberKind.OUTAGE_SIGNAL,
            )
            rows.append(
                CyberItem(
                    event.id,
                    kind,
                    event.title[:300],
                    summary,
                    event.url or "",
                    event.source_id,
                    spec.name,
                    spec.organisation,
                    event.published_at,
                    event.observed_at,
                    event.country_iso,
                    event.grade,
                    mentions,
                    _kev(event) if kind is CyberKind.KNOWN_EXPLOITED_VULNERABILITY else None,
                    themes,
                )
            )
        rows.sort(key=lambda item: (item.published_at, item.id), reverse=True)
        return tuple(rows)

    def _source(self, key: str, count: int) -> CyberSource:
        spec, health = self._sources[key], self._health.get(key)
        return CyberSource(
            key,
            spec.name,
            spec.organisation,
            spec.homepage,
            health.status.value,
            health.last_success,
            health.last_error_at,
            count,
        )


def _safe_link(value: str | None) -> bool:
    if not value or len(value) > 2_048 or any(ord(char) < 32 for char in value):
        return False
    try:
        url = urlsplit(value)
        return bool(
            url.scheme in {"https", "http"}
            and url.hostname
            and url.username is None
            and url.password is None
        )
    except ValueError:
        return False


def _kev(event: Event) -> CyberKev | None:
    if event.published_at is None or event.source_id != "cisa_kev":
        return None

    def attribute(key: str) -> str:
        value = event.attributes.get(key)
        return value[:500] if isinstance(value, str) else ""

    return CyberKev(
        attribute("cve"),
        attribute("vendor"),
        attribute("product"),
        event.published_at.astimezone(UTC).date(),
        attribute("due_date"),
        attribute("ransomware"),
        attribute("cwes"),
        attribute("required_action"),
    )


def _released(row: CyberItem, actors_enabled: bool, states: Mapping[str, str]) -> CyberItem:
    """Derived name matches and their state lens follow the reference source control."""
    if not actors_enabled:
        return replace(row, actor_mentions=())
    if CyberTheme.NATION_STATE not in row.themes and any(
        mention.group_id in states for mention in row.actor_mentions
    ):
        return replace(row, themes=(CyberTheme.NATION_STATE, *row.themes))
    return row


def _counts(counts: Counter[CyberKind]) -> tuple[CyberKindCount, ...]:
    return tuple(CyberKindCount(kind, counts[kind]) for kind in CyberKind)


def _days(start: datetime, end: datetime) -> tuple[date, ...]:
    days: list[date] = []
    day = start.date()
    while day <= (end - timedelta(microseconds=1)).date():
        days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def _published_day(row: CyberItem) -> date:
    return row.published_at.astimezone(UTC).date()


def _timeline(rows: list[CyberItem], days: tuple[date, ...]) -> tuple[CyberDailyCount, ...]:
    result: list[CyberDailyCount] = []
    for day in days:
        counts = Counter(row.kind for row in rows if _published_day(row) == day)
        result.append(CyberDailyCount(day, sum(counts.values()), _counts(counts)))
    return tuple(result)


def _themes(rows: list[CyberItem], days: tuple[date, ...]) -> tuple[CyberThemeTally, ...]:
    result: list[CyberThemeTally] = []
    for theme in CyberTheme:
        matched = [row for row in rows if theme in row.themes]
        by_day = Counter(_published_day(row) for row in matched)
        result.append(CyberThemeTally(theme, len(matched), tuple(by_day[day] for day in days)))
    return tuple(result)


def _state_mentions(
    rows: list[CyberItem], states: Mapping[str, str]
) -> tuple[CyberStateTally, ...]:
    """Each record counts once per state, however many matched names it carries."""
    counts: Counter[str] = Counter()
    groups: dict[str, Counter[str]] = {}
    for row in rows:
        per_row: dict[str, set[str]] = {}
        for mention in row.actor_mentions:
            state = states.get(mention.group_id)
            if state:
                per_row.setdefault(state, set()).add(mention.group_id)
        for state, group_ids in per_row.items():
            counts[state] += 1
            groups.setdefault(state, Counter()).update(group_ids)
    return tuple(
        CyberStateTally(
            state,
            count,
            tuple(group for group, _ in groups[state].most_common(MAX_STATE_GROUPS)),
        )
        for state, count in counts.most_common(20)
    )
