"""Response models for events, the live store and source health."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel

from ase.application.feeds.health import SourceHealth, SourceStatus
from ase.application.ports.feeds import StoreStats
from ase.domain.events import Category, Event, GeoConfidence, JsonScalar, Reliability
from ase.domain.sources import SourceKind, SourceSpec


class PointOut(BaseModel):
    lon: float
    lat: float


class EventOut(BaseModel):
    id: str
    source_id: str
    category: Category
    subtype: str
    title: str
    summary: str | None
    url: str | None
    published_at: datetime | None
    observed_at: datetime
    language: str
    title_en: str | None
    point: PointOut | None
    geo_confidence: GeoConfidence
    country_iso: str | None
    tags: list[str]
    severity: float | None
    reliability: Reliability
    credibility: int
    grade: str
    grade_rationale: str
    story_id: str | None
    attributes: dict[str, JsonScalar]

    @classmethod
    def from_event(cls, event: Event) -> Self:
        return cls(
            id=event.id,
            source_id=event.source_id,
            category=event.category,
            subtype=event.subtype,
            title=event.title,
            summary=event.summary,
            url=event.url,
            published_at=event.published_at,
            observed_at=event.observed_at,
            language=event.language,
            title_en=event.title_en,
            point=PointOut(lon=event.point.lon, lat=event.point.lat) if event.point else None,
            geo_confidence=event.geo_confidence,
            country_iso=event.country_iso,
            tags=sorted(event.tags),
            severity=event.severity,
            reliability=event.reliability,
            credibility=int(event.credibility),
            grade=event.grade,
            grade_rationale=event.grade_rationale,
            story_id=event.story_id,
            attributes=dict(event.attributes),
        )


class EventsOut(BaseModel):
    items: list[EventOut]
    count: int


class CategoryStatsOut(BaseModel):
    category: Category
    count: int
    oldest: datetime | None
    newest: datetime | None


class StoreStatsOut(BaseModel):
    total: int
    estimated_bytes: int
    budget_bytes: int
    per_category: list[CategoryStatsOut]

    @classmethod
    def from_stats(cls, stats: StoreStats) -> Self:
        return cls(
            total=stats.total,
            estimated_bytes=stats.estimated_bytes,
            budget_bytes=stats.budget_bytes,
            per_category=[
                CategoryStatsOut(
                    category=item.category,
                    count=item.count,
                    oldest=item.oldest,
                    newest=item.newest,
                )
                for item in stats.per_category
            ],
        )


class SourceHealthOut(BaseModel):
    source_id: str
    status: SourceStatus
    last_success: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    consecutive_failures: int
    items_last_poll: int
    last_latency_ms: float | None
    next_poll_at: datetime | None
    polls: int

    @classmethod
    def from_health(cls, health: SourceHealth) -> Self:
        return cls(
            source_id=health.source_id,
            status=health.status,
            last_success=health.last_success,
            last_error=health.last_error,
            last_error_at=health.last_error_at,
            consecutive_failures=health.consecutive_failures,
            items_last_poll=health.items_last_poll,
            last_latency_ms=health.last_latency_ms,
            next_poll_at=health.next_poll_at,
            polls=health.polls,
        )


class SourceOut(BaseModel):
    enabled: bool = True
    test_available: bool = True
    environment_disabled: bool = False
    id: str
    name: str
    organisation: str
    category: Category
    kind: SourceKind
    url: str
    reliability: Reliability
    poll_interval_seconds: int
    language: str
    licence_note: str
    homepage: str
    requires_key: bool
    instrument: bool
    flags: list[str]
    health: SourceHealthOut

    @classmethod
    def from_spec(cls, spec: SourceSpec, health: SourceHealth) -> Self:
        return cls(
            id=spec.id,
            name=spec.name,
            organisation=spec.organisation,
            category=spec.category,
            kind=spec.kind,
            url=spec.url,
            reliability=spec.reliability,
            poll_interval_seconds=int(spec.poll_interval.total_seconds()),
            language=spec.language,
            licence_note=spec.licence_note,
            homepage=spec.homepage,
            requires_key=spec.requires_key,
            instrument=spec.instrument,
            flags=sorted(spec.flags),
            health=SourceHealthOut.from_health(health),
        )


class SourcesOut(BaseModel):
    items: list[SourceOut]
