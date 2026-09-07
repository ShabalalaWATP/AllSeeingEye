"""Indicators and alerts: standing rules over the live picture that fire when a threshold is met.

An indicator watches part of the picture (an area, nations, categories, keywords) and fires
when at least `threshold` matching items were published inside its window. A cooldown stops
the same indicator firing again every cycle while the situation persists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from ase.domain.events import BoundingBox, Category, Event
from ase.domain.evidence_time import publication_order

MAX_KEYWORDS = 20
MAX_THRESHOLD = 10_000
MIN_WINDOW_MINUTES = 5
MAX_WINDOW_MINUTES = 7 * 24 * 60
MAX_COOLDOWN_MINUTES = 24 * 60
MAX_EVIDENCE = 20
ALERT_RETENTION = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class Indicator:
    id: UUID
    name: str
    description: str
    plan_id: UUID | None
    countries: tuple[str, ...]
    bbox: BoundingBox | None
    categories: tuple[Category, ...]
    keywords: tuple[str, ...]
    threshold: int
    window_minutes: int
    cooldown_minutes: int
    severity_floor: float
    report_template: str | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    team_id: UUID | None = None

    @property
    def window(self) -> timedelta:
        return timedelta(minutes=self.window_minutes)

    @property
    def cooldown(self) -> timedelta:
        return timedelta(minutes=self.cooldown_minutes)

    def in_scope(self, event: Event) -> bool:
        """Inside the box when there is one, else filed under one of the nations, else anywhere."""
        if self.bbox is not None:
            point = event.point
            if point is None:
                return False
            return (
                self.bbox.west <= point.lon <= self.bbox.east
                and self.bbox.south <= point.lat <= self.bbox.north
            )
        if self.countries:
            return event.country_iso is not None and event.country_iso.upper() in self.countries
        return True

    def matches(self, event: Event) -> bool:
        if not self.in_scope(event):
            return False
        if self.categories and event.category not in self.categories:
            return False
        if (event.severity or 0.0) < self.severity_floor:
            return False
        if not self.keywords:
            return True
        text = f"{event.title} {event.summary or ''}".lower()
        return any(word.lower() in text for word in self.keywords)


@dataclass(frozen=True, slots=True)
class Alert:
    id: UUID
    indicator_id: UUID | None
    fired_at: datetime
    title: str
    summary: str
    count: int
    threshold: int
    event_ids: tuple[str, ...]
    countries: tuple[str, ...]
    schedule_id: UUID | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None
    report_id: UUID | None = None
    created_by: UUID | None = None
    team_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Firing:
    count: int
    evidence: tuple[Event, ...]
    countries: tuple[str, ...]


def describe_window(minutes: int) -> str:
    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days} d"
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


def evaluate(
    indicator: Indicator,
    events: list[Event],
    now: datetime,
    last_fired: datetime | None,
) -> Firing | None:
    """The firing for this cycle, or None when the rule is quiet or still cooling down."""
    if not indicator.enabled:
        return None
    if last_fired is not None and now - last_fired < indicator.cooldown:
        return None
    since = now - indicator.window
    matched = [
        e
        for e in events
        if e.published_at is not None and e.published_at >= since and indicator.matches(e)
    ]
    if len(matched) < indicator.threshold:
        return None
    matched.sort(key=publication_order, reverse=True)
    countries = tuple(dict.fromkeys(e.country_iso for e in matched if e.country_iso))
    return Firing(len(matched), tuple(matched[:MAX_EVIDENCE]), countries)


def alert_from(indicator: Indicator, firing: Firing, alert_id: UUID, now: datetime) -> Alert:
    noun = "item" if firing.count == 1 else "items"
    title = (
        f"{indicator.name}: {firing.count} {noun} in the last "
        f"{describe_window(indicator.window_minutes)}"
    )
    summary = "; ".join(e.title for e in firing.evidence[:5])[:1000]
    return Alert(
        id=alert_id,
        indicator_id=indicator.id,
        fired_at=now,
        title=title[:200],
        summary=summary,
        count=firing.count,
        threshold=indicator.threshold,
        event_ids=tuple(e.id for e in firing.evidence),
        countries=firing.countries,
        created_by=indicator.created_by,
        team_id=indicator.team_id,
    )
