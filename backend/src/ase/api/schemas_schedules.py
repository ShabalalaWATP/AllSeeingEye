"""Schemas for scheduled products."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from ase.application.schedules.manage import ScheduleInput
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_changes import ResearchChange
from ase.domain.research_scope import MAX_RESEARCH_HOURS
from ase.domain.schedules import Schedule


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
    cadence: str = Field(default="daily", max_length=16)
    weekday: int = Field(default=0, ge=0, le=6)
    monthday: int = Field(default=1, ge=1, le=31)
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
            cadence=self.cadence,
            weekday=self.weekday,
            monthday=self.monthday,
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


class ScheduleOut(BaseModel):
    id: UUID
    name: str
    template_id: str
    country_iso: str | None
    country_isos: list[str]
    plan_id: UUID | None
    hour_utc: int
    cadence: str
    weekday: int
    monthday: int
    window_hours: int | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    next_run_at: datetime
    last_run_at: datetime | None
    last_report_id: UUID | None
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
            cadence=schedule.cadence,
            weekday=schedule.weekday,
            monthday=schedule.monthday,
            window_hours=schedule.window_hours,
            enabled=schedule.enabled,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_report_id=schedule.last_report_id,
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
