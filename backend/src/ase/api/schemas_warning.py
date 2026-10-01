"""Schemas for alert rules (historically "indicators") and the alerts they raise."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ase.api.schemas_research_area import ResearchAreaIn, ResearchAreaOut
from ase.application.warning.indicators import IndicatorInput
from ase.domain.events import Category
from ase.domain.warning import Alert, Indicator

# Values are rejected rather than truncated: a shortened country code or keyword would
# silently change what the rule watches.
CountryCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z]{2}$")]
Keyword = Annotated[str, StringConstraints(max_length=60)]


class IndicatorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    plan_id: UUID | None = None
    countries: list[CountryCode] = Field(default_factory=list, max_length=50)
    bbox: tuple[float, float, float, float] | None = None
    research_area: ResearchAreaIn | None = None
    categories: list[Category] = Field(default_factory=list, max_length=20)
    keywords: list[Keyword] = Field(default_factory=list, max_length=20)
    threshold: int = Field(default=1, ge=1, le=10_000)
    window_minutes: int = Field(default=60, ge=5, le=10_080)
    cooldown_minutes: int = Field(default=60, ge=1, le=1_440)
    severity_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    report_template: str | None = Field(default=None, max_length=40)
    enabled: bool = True
    team_id: UUID | None = None

    def to_input(self) -> IndicatorInput:
        return IndicatorInput(
            name=self.name,
            description=self.description,
            plan_id=self.plan_id,
            countries=list(self.countries),
            bbox=self.bbox,
            research_area=self.research_area.to_domain() if self.research_area else None,
            categories=self.categories,
            keywords=list(self.keywords),
            threshold=self.threshold,
            window_minutes=self.window_minutes,
            cooldown_minutes=self.cooldown_minutes,
            severity_floor=self.severity_floor,
            report_template=self.report_template,
            enabled=self.enabled,
            team_id=self.team_id,
        )


class IndicatorUpdateIn(IndicatorIn):
    """An edit names the revision (`updated_at`) it was made from; stale edits get 409.

    Removing every location, category or keyword restriction needs `confirm_wider_scope`.
    Pause and resume are edits of `enabled` that send the rule's other values unchanged.
    """

    expected_updated_at: datetime
    confirm_wider_scope: bool = False


class IndicatorOut(BaseModel):
    research_area: ResearchAreaOut | None = None
    id: UUID
    name: str
    description: str
    plan_id: UUID | None
    countries: list[str]
    bbox: list[float] | None
    categories: list[Category]
    keywords: list[str]
    threshold: int
    window_minutes: int
    cooldown_minutes: int
    severity_floor: float
    report_template: str | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    team_id: UUID | None

    @classmethod
    def from_indicator(cls, indicator: Indicator) -> IndicatorOut:
        box = indicator.bbox
        return cls(
            id=indicator.id,
            research_area=ResearchAreaOut.model_validate(indicator.research_area)
            if indicator.research_area
            else None,
            name=indicator.name,
            description=indicator.description,
            plan_id=indicator.plan_id,
            countries=list(indicator.countries),
            bbox=None if box is None else [box.west, box.south, box.east, box.north],
            categories=list(indicator.categories),
            keywords=list(indicator.keywords),
            threshold=indicator.threshold,
            window_minutes=indicator.window_minutes,
            cooldown_minutes=indicator.cooldown_minutes,
            severity_floor=indicator.severity_floor,
            report_template=indicator.report_template,
            enabled=indicator.enabled,
            created_by=indicator.created_by,
            created_at=indicator.created_at,
            updated_at=indicator.updated_at,
            team_id=indicator.team_id,
        )


class IndicatorsOut(BaseModel):
    items: list[IndicatorOut]


class AlertOut(BaseModel):
    id: UUID
    indicator_id: UUID | None
    schedule_id: UUID | None
    annotation_monitor_id: UUID | None
    annotation_transition_id: UUID | None
    fired_at: datetime
    title: str
    summary: str
    count: int
    threshold: int
    event_ids: list[str]
    countries: list[str]
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    report_id: UUID | None
    created_by: UUID | None
    team_id: UUID | None
    # The personal owner's display name on list views; null for team alerts.
    owner_name: str | None = None

    @classmethod
    def from_alert(cls, alert: Alert, owner_name: str | None = None) -> AlertOut:
        return cls(
            id=alert.id,
            indicator_id=alert.indicator_id,
            schedule_id=alert.schedule_id,
            annotation_monitor_id=alert.annotation_monitor_id,
            annotation_transition_id=alert.annotation_transition_id,
            fired_at=alert.fired_at,
            title=alert.title,
            summary=alert.summary,
            count=alert.count,
            threshold=alert.threshold,
            event_ids=list(alert.event_ids),
            countries=list(alert.countries),
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            report_id=alert.report_id,
            created_by=alert.created_by,
            team_id=alert.team_id,
            owner_name=owner_name,
        )


class AlertsOut(BaseModel):
    items: list[AlertOut]
    unacknowledged: int
