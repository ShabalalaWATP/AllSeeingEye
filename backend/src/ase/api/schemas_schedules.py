"""Schemas for scheduled products."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.schedules.manage import ScheduleInput
from ase.domain.schedules import Schedule


class ScheduleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    template_id: str = Field(min_length=1, max_length=40)
    country_iso: str | None = Field(default=None, max_length=2)
    plan_id: UUID | None = None
    hour_utc: int = Field(default=6, ge=0, le=23)
    cadence: str = Field(default="daily", max_length=16)
    weekday: int = Field(default=0, ge=0, le=6)
    window_hours: int | None = Field(default=None, ge=1, le=336)
    enabled: bool = True
    team_id: UUID | None = None

    def to_input(self) -> ScheduleInput:
        return ScheduleInput(
            name=self.name,
            template_id=self.template_id,
            country_iso=self.country_iso,
            plan_id=self.plan_id,
            hour_utc=self.hour_utc,
            cadence=self.cadence,
            weekday=self.weekday,
            window_hours=self.window_hours,
            enabled=self.enabled,
            team_id=self.team_id,
        )


class ScheduleOut(BaseModel):
    id: UUID
    name: str
    template_id: str
    country_iso: str | None
    plan_id: UUID | None
    hour_utc: int
    cadence: str
    weekday: int
    window_hours: int | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    next_run_at: datetime
    last_run_at: datetime | None
    last_report_id: UUID | None
    last_error: str | None
    team_id: UUID | None

    @classmethod
    def from_schedule(cls, schedule: Schedule) -> ScheduleOut:
        return cls(
            id=schedule.id,
            name=schedule.name,
            template_id=schedule.template_id,
            country_iso=schedule.country_iso,
            plan_id=schedule.plan_id,
            hour_utc=schedule.hour_utc,
            cadence=schedule.cadence,
            weekday=schedule.weekday,
            window_hours=schedule.window_hours,
            enabled=schedule.enabled,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_report_id=schedule.last_report_id,
            last_error=schedule.last_error,
            team_id=schedule.team_id,
        )


class SchedulesOut(BaseModel):
    items: list[ScheduleOut]
