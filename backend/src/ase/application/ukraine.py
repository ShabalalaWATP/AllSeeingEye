"""Ukraine war board: what retained reporting, published claims and the control snapshot say."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.trackers import ConflictDirectory
from ase.domain.events import Category, Event
from ase.domain.ukraine.confirmed import CivilianHarm, ConfirmedLosses
from ase.domain.ukraine.control import ControlSnapshot
from ase.domain.ukraine.lenses import Lens, lenses_for
from ase.domain.ukraine.losses import MAX_CLAIMS, ClaimedLosses, claim_from_attributes, war_day
from ase.domain.ukraine.updates import UpdateGroup, concerns_war, event_text, update_group

CONFLICT_ID = "ukraine"
CLAIM_SOURCE = "ukraine_general_staff"
ASSESSMENT_SOURCE = "isw_assessments"
WINDOW = timedelta(days=14)
CLAIM_WINDOW = timedelta(days=100)
POOL = 3_000
PER_GROUP = 40
CATEGORIES = frozenset(
    {Category.NEWS, Category.POLITICAL, Category.CONFLICT, Category.HUMANITARIAN}
)


@dataclass(frozen=True, slots=True)
class UpdateEntry:
    event: Event
    group: UpdateGroup
    lenses: frozenset[Lens]


@dataclass(frozen=True, slots=True)
class Freshness:
    control_assessed: date | None
    assessment_published: datetime | None
    claim_reported: date | None
    latest_update: datetime | None


@dataclass(frozen=True, slots=True)
class LensSeries:
    """Items per day for one lens, split by reporting group, over the window."""

    lens: Lens
    days: tuple[date, ...]
    groups: Mapping[UpdateGroup, tuple[int, ...]]


@dataclass(frozen=True, slots=True)
class UkraineBoard:
    generated_at: datetime
    day_number: int
    day_basis: Literal["claimed", "computed"]
    window_days: int
    events_scanned: int
    updates: tuple[UpdateEntry, ...]
    lens_counts: Mapping[Lens, int]
    claims: tuple[ClaimedLosses, ...]
    control: ControlSnapshot | None
    freshness: Freshness
    confirmed: ConfirmedLosses | None
    civilian_harm: CivilianHarm | None
    lens_series: tuple[LensSeries, ...]


class UkraineBoardService:
    def __init__(
        self,
        store: EventStore,
        clock: Clock,
        conflicts: ConflictDirectory,
        control: ControlSnapshot | None,
        confirmed: ConfirmedLosses | None = None,
        civilian_harm: CivilianHarm | None = None,
    ) -> None:
        self._store, self._clock, self._conflicts, self._control = store, clock, conflicts, control
        self._confirmed, self._civilian_harm = confirmed, civilian_harm

    @property
    def control(self) -> ControlSnapshot | None:
        return self._control

    def board(self) -> UkraineBoard:
        now = self._clock.now()
        events = self._events(now)
        per_group: Counter[UpdateGroup] = Counter()
        updates: list[UpdateEntry] = []
        for event in events:
            if event.source_id == CLAIM_SOURCE:
                continue  # Claims are figures on the page, not headlines.
            group = update_group(event.source_id)
            if per_group[group] >= PER_GROUP:
                continue
            per_group[group] += 1
            updates.append(UpdateEntry(event, group, lenses_for(event_text(event))))
        claims = self._claims(now)
        latest_claim = claims[-1] if claims else None
        day = latest_claim.day if latest_claim is not None else war_day(now.date())
        assessments = [e for e in events if e.source_id == ASSESSMENT_SOURCE and e.published_at]
        return UkraineBoard(
            generated_at=now,
            day_number=day,
            day_basis="claimed" if latest_claim is not None else "computed",
            window_days=WINDOW.days,
            events_scanned=len(events),
            updates=tuple(updates),
            lens_counts=Counter(lens for entry in updates for lens in entry.lenses),
            claims=claims,
            control=self._control,
            confirmed=self._confirmed,
            civilian_harm=self._civilian_harm,
            lens_series=lens_series(updates, now),
            freshness=Freshness(
                control_assessed=self._control.assessment_date if self._control else None,
                assessment_published=max(
                    (e.published_at for e in assessments if e.published_at), default=None
                ),
                claim_reported=latest_claim.reported_on if latest_claim else None,
                latest_update=_recency(updates[0].event) if updates else None,
            ),
        )

    def _events(self, now: datetime) -> list[Event]:
        """Everything in the box or filed under the belligerents that names the war."""
        conflict = self._conflicts.get(CONFLICT_ID)
        since = now - WINDOW
        queries = [EventQuery(country_iso="UA", categories=CATEGORIES, since=since, limit=POOL)]
        if conflict is not None:
            queries.append(
                EventQuery(bbox=conflict.bbox, categories=CATEGORIES, since=since, limit=POOL)
            )
            queries.extend(
                EventQuery(country_iso=iso, categories=CATEGORIES, since=since, limit=POOL)
                for iso in conflict.countries
                if iso != "UA"
            )
        seen: dict[str, Event] = {}
        for query in queries:
            for event in self._store.query(query):
                if event.id not in seen and concerns_war(event):
                    seen[event.id] = event
        return sorted(seen.values(), key=_recency, reverse=True)

    def _claims(self, now: datetime) -> tuple[ClaimedLosses, ...]:
        rows = self._store.query(
            EventQuery(
                source_ids=frozenset({CLAIM_SOURCE}), since=now - CLAIM_WINDOW, limit=MAX_CLAIMS
            )
        )
        by_day: dict[date, ClaimedLosses] = {}
        for event in rows:
            if event.published_at is None:
                continue
            claim = claim_from_attributes(event.published_at.date(), event.url, event.attributes)
            if claim is not None:
                by_day[claim.reported_on] = claim
        return tuple(by_day[key] for key in sorted(by_day))


def _recency(event: Event) -> datetime:
    return event.published_at or event.observed_at


def lens_series(updates: list[UpdateEntry], now: datetime) -> tuple[LensSeries, ...]:
    """Counts per day and group for each lens; a text match per item, never a judgement."""
    days = tuple(now.date() - timedelta(days=offset) for offset in range(WINDOW.days - 1, -1, -1))
    index = {day: position for position, day in enumerate(days)}
    series: list[LensSeries] = []
    for lens in Lens:
        counts = {group: [0] * len(days) for group in UpdateGroup}
        for entry in updates:
            position = index.get(_recency(entry.event).date())
            if lens in entry.lenses and position is not None:
                counts[entry.group][position] += 1
        series.append(
            LensSeries(
                lens=lens,
                days=days,
                groups={group: tuple(values) for group, values in counts.items()},
            )
        )
    return tuple(series)
