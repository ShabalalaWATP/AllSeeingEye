"""A bounded, read-only summary of one team's shared work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.team_board import TeamBoardPostView
from ase.domain.teams import MembershipRole, Team

DASHBOARD_ITEM_LIMIT = 5
ACTION_LOOKBACK_DAYS = 30


class TeamActionKind(StrEnum):
    OWNER_NOT_MEMBER = "owner_not_member"
    EDITION_FAILED = "edition_failed"
    EDITION_BLOCKED = "edition_blocked"


@dataclass(frozen=True, slots=True)
class TeamReportSummary:
    id: UUID
    title: str
    template: str
    status: str
    latest_version: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TeamScheduledRun:
    schedule_id: UUID
    name: str
    cadence: str
    next_run_at: datetime


@dataclass(frozen=True, slots=True)
class TeamActionItem:
    kind: TeamActionKind
    schedule_id: UUID
    schedule_name: str
    occurred_at: datetime
    edition_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class TeamDashboard:
    team: Team
    role: MembershipRole | None
    member_count: int
    pinned: tuple[TeamBoardPostView, ...]
    unread_count: int
    recent_reports: tuple[TeamReportSummary, ...]
    upcoming_runs: tuple[TeamScheduledRun, ...]
    action_items: tuple[TeamActionItem, ...]
