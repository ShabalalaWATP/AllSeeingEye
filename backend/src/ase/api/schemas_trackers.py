"""Response models for the tracker boards and detail views."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel

from ase.api.schemas_events import EventOut
from ase.application.trackers.boards import ConflictDetail, HazardDetail
from ase.domain.conflict_evidence import evidence_groups
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
    fatalities_7d: int | None
    fatalities_upper_7d: int | None = None
    fatalities_unknown_incidents: int = 0
    fatalities_disputed_incidents: int = 0
    other_activity_7d: int = 0
    unknown_date_reports: int = 0
    collapsed_reports_7d: int = 0
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
            fatalities_upper_7d=card.fatalities_upper_7d,
            fatalities_unknown_incidents=card.fatalities_unknown_incidents,
            fatalities_disputed_incidents=card.fatalities_disputed_incidents,
            other_activity_7d=card.other_activity_7d,
            unknown_date_reports=card.unknown_date_reports,
            collapsed_reports_7d=card.collapsed_reports_7d,
            max_severity=card.max_severity,
            latest=_event(card.latest),
            top=_event(card.top),
        )


class ConflictBoardOut(BaseModel):
    items: list[ConflictCardOut]


class ConflictEvidenceGroupOut(BaseModel):
    representative_id: str
    report_ids: list[str]
    source_ids: list[str]
    report_count: int


class ConflictDetailOut(BaseModel):
    card: ConflictCardOut
    timeline: list[DayBucketOut]
    events: list[EventOut]
    evidence_groups: list[ConflictEvidenceGroupOut]

    @classmethod
    def from_detail(cls, detail: ConflictDetail) -> Self:
        return cls(
            card=ConflictCardOut.from_card(detail.card),
            timeline=[DayBucketOut.from_bucket(bucket) for bucket in detail.timeline],
            events=[EventOut.from_event(event) for event in detail.events],
            evidence_groups=[
                ConflictEvidenceGroupOut(
                    representative_id=group[0].id,
                    report_ids=[event.id for event in group],
                    source_ids=sorted({event.source_id for event in group}),
                    report_count=len(group),
                )
                for group in evidence_groups(detail.events)
            ],
        )
