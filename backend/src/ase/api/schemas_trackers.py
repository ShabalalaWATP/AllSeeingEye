"""Response models for the tracker boards and detail views."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel

from ase.api.schemas_events import EventOut
from ase.application.trackers.boards import ConflictDetail, HazardDetail
from ase.domain.events import Event
from ase.domain.trackers import (
    HAZARD_TITLES,
    Activity,
    Conflict,
    ConflictCard,
    DayBucket,
    Hazard,
    HazardCard,
)


def _event(event: Event | None) -> EventOut | None:
    return EventOut.from_event(event) if event is not None else None


class ActivityOut(BaseModel):
    last_24h: int
    last_7d: int
    previous_7d: int
    trend: float | None

    @classmethod
    def from_activity(cls, activity: Activity) -> Self:
        return cls(
            last_24h=activity.last_24h,
            last_7d=activity.last_7d,
            previous_7d=activity.previous_7d,
            trend=activity.trend,
        )


class DayBucketOut(BaseModel):
    day: date
    count: int
    max_severity: float | None

    @classmethod
    def from_bucket(cls, bucket: DayBucket) -> Self:
        return cls(day=bucket.day, count=bucket.count, max_severity=bucket.max_severity)


class HazardCardOut(BaseModel):
    hazard: Hazard
    title: str
    activity: ActivityOut
    red_alerts: int
    max_severity: float | None
    countries: list[str]
    latest: EventOut | None
    top: EventOut | None

    @classmethod
    def from_card(cls, card: HazardCard) -> Self:
        return cls(
            hazard=card.hazard,
            title=HAZARD_TITLES[card.hazard],
            activity=ActivityOut.from_activity(card.activity),
            red_alerts=card.red_alerts,
            max_severity=card.max_severity,
            countries=list(card.countries),
            latest=_event(card.latest),
            top=_event(card.top),
        )


class HazardBoardOut(BaseModel):
    items: list[HazardCardOut]


class HazardDetailOut(BaseModel):
    card: HazardCardOut
    timeline: list[DayBucketOut]
    events: list[EventOut]

    @classmethod
    def from_detail(cls, detail: HazardDetail) -> Self:
        return cls(
            card=HazardCardOut.from_card(detail.card),
            timeline=[DayBucketOut.from_bucket(bucket) for bucket in detail.timeline],
            events=[EventOut.from_event(event) for event in detail.events],
        )


class ConflictOut(BaseModel):
    id: str
    name: str
    status: str
    countries: list[str]
    bbox: list[float]
    belligerents: list[str]
    keywords: list[str]
    summary: str

    @classmethod
    def from_conflict(cls, conflict: Conflict) -> Self:
        box = conflict.bbox
        return cls(
            id=conflict.id,
            name=conflict.name,
            status=conflict.status,
            countries=list(conflict.countries),
            bbox=[box.west, box.south, box.east, box.north],
            belligerents=list(conflict.belligerents),
            keywords=list(conflict.keywords),
            summary=conflict.summary,
        )


class ConflictCardOut(BaseModel):
    conflict: ConflictOut
    activity: ActivityOut
    reporting_7d: int
    fatalities_7d: int
    max_severity: float | None
    latest: EventOut | None
    top: EventOut | None

    @classmethod
    def from_card(cls, card: ConflictCard) -> Self:
        return cls(
            conflict=ConflictOut.from_conflict(card.conflict),
            activity=ActivityOut.from_activity(card.activity),
            reporting_7d=card.reporting_7d,
            fatalities_7d=card.fatalities_7d,
            max_severity=card.max_severity,
            latest=_event(card.latest),
            top=_event(card.top),
        )


class ConflictBoardOut(BaseModel):
    items: list[ConflictCardOut]


class ConflictDetailOut(BaseModel):
    card: ConflictCardOut
    timeline: list[DayBucketOut]
    events: list[EventOut]

    @classmethod
    def from_detail(cls, detail: ConflictDetail) -> Self:
        return cls(
            card=ConflictCardOut.from_card(detail.card),
            timeline=[DayBucketOut.from_bucket(bucket) for bucket in detail.timeline],
            events=[EventOut.from_event(event) for event in detail.events],
        )
