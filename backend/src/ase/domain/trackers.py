"""Trackers (docs/04 section 5): boards computed from the live store, never stored.

A tracker card summarises one hazard or one conflict over the last fortnight: activity
now against the week before, the worst and the newest event, and where it is happening.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from ase.domain.conflict_evidence import (
    casualties,
    evidence_groups,
    is_conflict_context,
    is_violence,
    occurrence_time,
)
from ase.domain.events import BoundingBox, Category, Event
from ase.domain.evidence_time import publication_order

DAY = timedelta(days=1)
WEEK = timedelta(days=7)
TIMELINE_DAYS = 14
MAX_COUNTRIES = 12
RED_SEVERITY = 0.85


class Hazard(StrEnum):
    EARTHQUAKE = "earthquake"
    TROPICAL_CYCLONE = "tropical_cyclone"
    FLOOD = "flood"
    VOLCANO = "volcano"
    WILDFIRE = "wildfire"
    DROUGHT = "drought"
    TSUNAMI = "tsunami"
    SEVERE_WEATHER = "severe_weather"
    OTHER = "other"


HAZARD_TITLES: dict[Hazard, str] = {
    Hazard.EARTHQUAKE: "Earthquakes",
    Hazard.TROPICAL_CYCLONE: "Tropical cyclones",
    Hazard.FLOOD: "Floods",
    Hazard.VOLCANO: "Volcanoes",
    Hazard.WILDFIRE: "Wildfires",
    Hazard.DROUGHT: "Drought",
    Hazard.TSUNAMI: "Tsunami",
    Hazard.SEVERE_WEATHER: "Severe weather",
    Hazard.OTHER: "Other hazards",
}

# Connector subtypes (GDACS, USGS, EONET, NHC, tsunami centres, NWS) folded into hazards.
HAZARD_ALIASES: dict[str, Hazard] = {
    "earthquake": Hazard.EARTHQUAKE,
    "earthquakes": Hazard.EARTHQUAKE,
    "tropical_cyclone": Hazard.TROPICAL_CYCLONE,
    "tropical_storm": Hazard.TROPICAL_CYCLONE,
    "hurricane": Hazard.TROPICAL_CYCLONE,
    "typhoon": Hazard.TROPICAL_CYCLONE,
    "severe_storms": Hazard.TROPICAL_CYCLONE,
    "flood": Hazard.FLOOD,
    "floods": Hazard.FLOOD,
    "volcano": Hazard.VOLCANO,
    "volcanoes": Hazard.VOLCANO,
    "wildfire": Hazard.WILDFIRE,
    "wildfires": Hazard.WILDFIRE,
    "drought": Hazard.DROUGHT,
    "tsunami": Hazard.TSUNAMI,
    "severe_weather": Hazard.SEVERE_WEATHER,
    "temp_extremes": Hazard.SEVERE_WEATHER,
    "snow": Hazard.SEVERE_WEATHER,
    "dust_haze": Hazard.SEVERE_WEATHER,
}


def hazard_of(event: Event) -> Hazard | None:
    """The hazard a disaster event belongs to; None for events of other categories."""
    if event.category is not Category.DISASTER:
        return None
    return HAZARD_ALIASES.get(event.subtype, Hazard.OTHER)


@dataclass(frozen=True, slots=True)
class Conflict:
    """A curated conflict or tension area (docs/04 section 5.1)."""

    id: str
    name: str
    status: str  # "war" or "tension"
    countries: tuple[str, ...]
    bbox: BoundingBox
    belligerents: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    summary: str = ""


@dataclass(frozen=True, slots=True)
class Activity:
    last_24h: int
    last_7d: int
    previous_7d: int

    @property
    def trend(self) -> float | None:
        """This week over the week before; None when there is no baseline."""
        if self.previous_7d == 0:
            return None
        return round(self.last_7d / self.previous_7d, 2)


@dataclass(frozen=True, slots=True)
class DayBucket:
    day: date
    count: int
    max_severity: float | None


@dataclass(frozen=True, slots=True)
class HazardCard:
    hazard: Hazard
    activity: Activity
    red_alerts: int
    max_severity: float | None
    countries: tuple[str, ...]
    latest: Event | None
    top: Event | None


@dataclass(frozen=True, slots=True)
class ConflictCard:
    conflict: Conflict
    activity: Activity
    reporting_7d: int
    fatalities_7d: int | None
    max_severity: float | None
    latest: Event | None
    top: Event | None
    fatalities_upper_7d: int | None = None
    fatalities_unknown_incidents: int = 0
    fatalities_disputed_incidents: int = 0
    other_activity_7d: int = 0
    unknown_date_reports: int = 0
    collapsed_reports_7d: int = 0


def activity(
    events: Iterable[Event],
    now: datetime,
    *,
    time_of: Callable[[Event], datetime | None] = lambda event: event.published_at,
) -> Activity:
    day_ago, week_ago, fortnight_ago = now - DAY, now - WEEK, now - 2 * WEEK
    last_24h = last_7d = previous_7d = 0
    for event in events:
        when = time_of(event)
        if when is None or when > now:
            continue
        if when >= day_ago:
            last_24h += 1
        if when >= week_ago:
            last_7d += 1
        elif when >= fortnight_ago:
            previous_7d += 1
    return Activity(last_24h=last_24h, last_7d=last_7d, previous_7d=previous_7d)


def timeline(
    events: Iterable[Event],
    now: datetime,
    days: int = TIMELINE_DAYS,
    *,
    time_of: Callable[[Event], datetime | None] = lambda event: event.published_at,
) -> tuple[DayBucket, ...]:
    """One bucket per UTC day, oldest first, ending today."""
    today = now.date()
    first = today - timedelta(days=days - 1)
    counts: Counter[date] = Counter()
    worst: dict[date, float] = {}
    for event in events:
        when = time_of(event)
        if when is None or when > now:
            continue
        day = when.date()
        if day < first or day > today:
            continue
        counts[day] += 1
        if event.severity is not None:
            worst[day] = max(worst.get(day, 0.0), event.severity)
    return tuple(
        DayBucket(day=first + timedelta(days=offset), count=counts[first + timedelta(days=offset)],
                  max_severity=worst.get(first + timedelta(days=offset)))
        for offset in range(days)
    )  # fmt: skip


def top_event(events: Iterable[Event]) -> Event | None:
    """The most severe event, newest first among equals."""
    return max(events, key=lambda e: (e.severity or 0.0, publication_order(e)), default=None)


def latest_event(events: Iterable[Event]) -> Event | None:
    return max(
        (e for e in events if e.published_at is not None), key=publication_order, default=None
    )


def _countries(events: Iterable[Event]) -> tuple[str, ...]:
    counts = Counter(event.country_iso for event in events if event.country_iso)
    return tuple(iso for iso, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))[
        :MAX_COUNTRIES
    ]


def _max_severity(events: Sequence[Event]) -> float | None:
    severities = [event.severity for event in events if event.severity is not None]
    return max(severities) if severities else None


def hazard_card(hazard: Hazard, events: Sequence[Event], now: datetime) -> HazardCard:
    """Summarise one hazard from its disaster events (already limited to the window)."""
    week = [
        event
        for event in events
        if event.published_at is not None and event.published_at >= now - WEEK
    ]
    red = sum(
        1 for event in week if "gdacs_red" in event.tags or (event.severity or 0.0) >= RED_SEVERITY
    )
    return HazardCard(
        hazard=hazard,
        activity=activity(events, now),
        red_alerts=red,
        max_severity=_max_severity(week),
        countries=_countries(week),
        latest=latest_event(events),
        top=top_event(week),
    )


def hazard_cards(events: Sequence[Event], now: datetime) -> tuple[HazardCard, ...]:
    """A card for every hazard, busiest first."""
    grouped: dict[Hazard, list[Event]] = {hazard: [] for hazard in Hazard}
    for event in events:
        hazard = hazard_of(event)
        if hazard is not None:
            grouped[hazard].append(event)
    cards = [hazard_card(hazard, items, now) for hazard, items in grouped.items()]
    cards.sort(key=lambda card: (-card.activity.last_7d, -card.red_alerts, card.hazard.value))
    return tuple(cards)


def conflict_card(conflict: Conflict, events: Sequence[Event], now: datetime) -> ConflictCard:
    """Count grouped violence reports by occurrence, with explicit evidence gaps."""
    groups = evidence_groups(event for event in events if is_violence(event))
    fighting = [group[0] for group in groups]
    week_groups = [
        group
        for group in groups
        if (when := occurrence_time(group[0])) is not None and now - WEEK <= when <= now
    ]
    week = [group[0] for group in week_groups]
    reporting = evidence_groups(
        event
        for event in events
        if is_conflict_context(event)
        and event.published_at is not None
        and now - WEEK <= event.published_at <= now
    )
    deaths = casualties(week_groups)
    other = [
        event
        for event in events
        if event.category is Category.CONFLICT
        and not is_violence(event)
        and (when := occurrence_time(event)) is not None
        and now - WEEK <= when <= now
    ]
    return ConflictCard(
        conflict=conflict,
        activity=activity(fighting, now, time_of=occurrence_time),
        reporting_7d=len(reporting),
        fatalities_7d=deaths.lower,
        max_severity=_max_severity(week),
        latest=max(
            (
                event
                for event in fighting
                if (when := occurrence_time(event)) is not None and when <= now
            ),
            key=lambda event: occurrence_time(event) or now,
            default=None,
        ),
        top=top_event(week),
        fatalities_upper_7d=deaths.upper,
        fatalities_unknown_incidents=deaths.unknown_incidents,
        fatalities_disputed_incidents=deaths.disputed_incidents,
        other_activity_7d=len(evidence_groups(other)),
        unknown_date_reports=sum(occurrence_time(event) is None for event in fighting),
        collapsed_reports_7d=sum(len(group) - 1 for group in week_groups),
    )
