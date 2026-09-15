"""Bounded JSON contract for the team overview."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel

from ase.api.schemas_team_board import TeamBoardPostOut
from ase.domain.team_dashboard import TeamDashboard


class TeamDashboardTeamOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    role: Literal["member", "manager"] | None
    member_count: int


class TeamDashboardReportOut(BaseModel):
    id: UUID
    title: str
    template: str
    status: str
    latest_version: int
    created_at: datetime


class TeamDashboardRunOut(BaseModel):
    schedule_id: UUID
    name: str
    cadence: str
    next_run_at: datetime


class TeamDashboardActionOut(BaseModel):
    kind: Literal["owner_not_member", "edition_failed", "edition_blocked"]
    schedule_id: UUID
    schedule_name: str
    occurred_at: datetime
    edition_id: UUID | None


class TeamDashboardOut(BaseModel):
    team: TeamDashboardTeamOut
    pinned: list[TeamBoardPostOut]
    unread_count: int
    recent_reports: list[TeamDashboardReportOut]
    upcoming_runs: list[TeamDashboardRunOut]
    action_items: list[TeamDashboardActionOut]

    @classmethod
    def from_dashboard(cls, value: TeamDashboard) -> Self:
        team = value.team
        return cls(
            team=TeamDashboardTeamOut(
                id=team.id,
                name=team.name,
                description=team.description,
                is_active=team.is_active,
                role=value.role.value if value.role else None,
                member_count=value.member_count,
            ),
            pinned=[TeamBoardPostOut.from_view(item) for item in value.pinned],
            unread_count=value.unread_count,
            recent_reports=[
                TeamDashboardReportOut(
                    id=item.id,
                    title=item.title,
                    template=item.template,
                    status=item.status,
                    latest_version=item.latest_version,
                    created_at=item.created_at,
                )
                for item in value.recent_reports
            ],
            upcoming_runs=[
                TeamDashboardRunOut(
                    schedule_id=item.schedule_id,
                    name=item.name,
                    cadence=item.cadence,
                    next_run_at=item.next_run_at,
                )
                for item in value.upcoming_runs
            ],
            action_items=[
                TeamDashboardActionOut(
                    kind=item.kind.value,
                    schedule_id=item.schedule_id,
                    schedule_name=item.schedule_name,
                    occurred_at=item.occurred_at,
                    edition_id=item.edition_id,
                )
                for item in value.action_items
            ],
        )
