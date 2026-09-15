"""Schemas for scheduled products."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from ase.api.schemas_research_area import ResearchAreaIn, ResearchAreaOut
from ase.application.schedules.definition import ScheduleInput
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_changes import ResearchChange
from ase.domain.research_scope import MAX_RESEARCH_HOURS
from ase.domain.schedules import CoverageState, Schedule
from ase.domain.subscription_recurrence import WindowPolicy


class ScheduleOccurrenceOut(BaseModel):
    scheduled_date: str
    local: datetime
    utc: datetime
    dst_resolution: str


class SchedulePreviewOut(BaseModel):
    next_three: list[ScheduleOccurrenceOut]
    collection_policy: WindowPolicy
    window_hours: int | None
    note: str = "Preview only. No report job or subscription has been created."


class ScheduleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    template_id: str = Field(min_length=1, max_length=40)
    country_iso: str | None = Field(default=None, max_length=2)
    country_isos: list[Annotated[str, Field(min_length=2, max_length=2)]] = Field(
        default_factory=list, max_length=8
    )
    plan_id: UUID | None = None
    hour_utc: int = Field(default=6, ge=0, le=23)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    local_hour: int | None = Field(default=None, ge=0, le=23)
    local_minute: int = Field(default=0, ge=0, le=59)
    collection_policy: WindowPolicy = WindowPolicy.ROLLING_SNAPSHOT
    cadence: str = Field(default="daily", max_length=16)
    weekday: int = Field(default=0, ge=0, le=6)
    monthday: int = Field(default=1, ge=1, le=31)
    anchor_month: int = Field(default=1, ge=1, le=12)
    conflict_id: str | None = Field(default=None, min_length=1, max_length=120)
    hazard: str | None = Field(default=None, min_length=1, max_length=40)
    research_area: ResearchAreaIn | None = None
    disclose_area_to_provider: StrictBool = False
    avoid_repetition: StrictBool = True
    window_hours: int | None = Field(default=None, ge=1, le=MAX_RESEARCH_HOURS)
    enabled: bool = True
    team_id: UUID | None = None
    notify_on_change: bool = False
    question: str | None = Field(default=None, max_length=1000)
    research_mode: ResearchMode | None = None
    research_languages: list[Annotated[str, Field(pattern=r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")]] = (
        Field(default_factory=lambda: ["en"], min_length=1, max_length=8)
    )
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = Field(default=None, max_length=300)
    research_web_search: StrictBool = False
    research_source_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] | None = Field(
        default=None, max_length=64
    )

    @field_validator("research_languages", mode="before")
    @classmethod
    def normalise_languages(cls, value: object) -> object:
        if isinstance(value, list):
            return [code.lower() if isinstance(code, str) else code for code in value]
        return value

    def to_input(self) -> ScheduleInput:
        return ScheduleInput(
            name=self.name,
            template_id=self.template_id,
            country_iso=self.country_iso,
            country_isos=tuple(self.country_isos),
            plan_id=self.plan_id,
            hour_utc=self.hour_utc,
            timezone=self.timezone,
            local_hour=self.local_hour,
            local_minute=self.local_minute,
            collection_policy=self.collection_policy,
            cadence=self.cadence,
            weekday=self.weekday,
            monthday=self.monthday,
            anchor_month=self.anchor_month,
            conflict_id=self.conflict_id,
            hazard=self.hazard,
            research_area=self.research_area.to_domain() if self.research_area else None,
            disclose_area_to_provider=self.disclose_area_to_provider,
            avoid_repetition=self.avoid_repetition,
            window_hours=self.window_hours,
            enabled=self.enabled,
            team_id=self.team_id,
            notify_on_change=self.notify_on_change,
            question=self.question,
            research_mode=self.research_mode,
            research_languages=tuple(self.research_languages),
            research_focus=self.research_focus,
            research_subject=self.research_subject,
            research_web_search=self.research_web_search,
            research_source_ids=tuple(self.research_source_ids)
            if self.research_source_ids is not None
            else None,
        )


class ScheduleFromBriefIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief_id: UUID
    brief_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    local_hour: int = Field(default=6, ge=0, le=23)
    local_minute: int = Field(default=0, ge=0, le=59)
    cadence: str = Field(default="daily", max_length=16)
    weekday: int = Field(default=0, ge=0, le=6)
    monthday: int = Field(default=1, ge=1, le=31)
    anchor_month: int = Field(default=1, ge=1, le=12)
    collection_policy: WindowPolicy = WindowPolicy.ROLLING_SNAPSHOT
    enabled: StrictBool = True
    notify_on_change: StrictBool = False
    avoid_repetition: StrictBool = True


class ScheduleOut(BaseModel):
    id: UUID
    name: str
    template_id: str
    country_iso: str | None
    country_isos: list[str]
    plan_id: UUID | None
    hour_utc: int
    timezone: str
    local_hour: int
    local_minute: int
    collection_policy: WindowPolicy
    brief_id: UUID | None
    brief_revision: int | None
    next_three: list[ScheduleOccurrenceOut]
    cadence: str
    weekday: int
    monthday: int
    anchor_month: int
    conflict_id: str | None
    hazard: str | None
    research_area: ResearchAreaOut | None
    disclose_area_to_provider: bool
    avoid_repetition: bool
    window_hours: int | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    next_run_at: datetime
    last_run_at: datetime | None
    last_report_id: UUID | None
    last_version_id: UUID | None
    last_outcome: ReportStatus | None
    last_coverage: CoverageState | None
    last_error: str | None
    team_id: UUID | None
    notify_on_change: bool
    last_change: ResearchChange | None
    last_change_summary: str | None
    question: str | None
    research_mode: ResearchMode | None
    research_languages: list[str]
    research_focus: ResearchFocus
    research_subject: str | None
    research_web_search: bool
    research_source_ids: list[str] | None

    @classmethod
    def from_schedule(cls, schedule: Schedule) -> ScheduleOut:
        return cls(
            id=schedule.id,
            name=schedule.name,
            template_id=schedule.template_id,
            country_iso=schedule.country_iso,
            country_isos=list(schedule.country_isos),
            plan_id=schedule.plan_id,
            hour_utc=schedule.hour_utc,
            timezone=schedule.timezone,
            local_hour=schedule.local_hour
            if schedule.local_hour is not None
            else schedule.hour_utc,
            local_minute=schedule.local_minute,
            collection_policy=schedule.collection_policy,
            brief_id=schedule.brief_id,
            brief_revision=schedule.brief_revision,
            next_three=[
                ScheduleOccurrenceOut(
                    scheduled_date=item.scheduled_date.isoformat(),
                    local=item.local,
                    utc=item.utc,
                    dst_resolution=item.dst_resolution,
                )
                for item in schedule.next_three
            ],
            cadence=schedule.cadence,
            weekday=schedule.weekday,
            monthday=schedule.monthday,
            anchor_month=schedule.anchor_month,
            conflict_id=schedule.conflict_id,
            hazard=schedule.hazard,
            research_area=ResearchAreaOut.model_validate(schedule.research_area)
            if schedule.research_area
            else None,
            disclose_area_to_provider=schedule.disclose_area_to_provider,
            avoid_repetition=schedule.avoid_repetition,
            window_hours=schedule.window_hours,
            enabled=schedule.enabled,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_report_id=schedule.last_report_id,
            last_version_id=schedule.last_version_id,
            last_outcome=schedule.last_outcome,
            last_coverage=schedule.last_coverage,
            last_error=schedule.last_error,
            team_id=schedule.team_id,
            notify_on_change=schedule.notify_on_change,
            last_change=schedule.last_change,
            last_change_summary=schedule.last_change.summary if schedule.last_change else None,
            question=schedule.question,
            research_mode=schedule.research_mode,
            research_languages=list(schedule.research_languages),
            research_focus=schedule.research_focus,
            research_subject=schedule.research_subject,
            research_web_search=schedule.research_web_search,
            research_source_ids=list(schedule.research_source_ids)
            if schedule.research_source_ids is not None
            else None,
        )


class SchedulesOut(BaseModel):
    items: list[ScheduleOut]
