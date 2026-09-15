"""SQL for the team overview: team and visibility filters always precede limits."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, exists, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.operational_models import ReportRow, ScheduleRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.access import Visibility
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.team_dashboard import (
    TeamActionItem,
    TeamActionKind,
    TeamReportSummary,
    TeamScheduledRun,
)

_ATTENTION = {
    EditionWorkflow.FAILED.value: TeamActionKind.EDITION_FAILED,
    EditionWorkflow.BLOCKED.value: TeamActionKind.EDITION_BLOCKED,
}


class SqlTeamDashboardQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent_reports(
        self, team_id: UUID, visibility: Visibility, limit: int
    ) -> list[TeamReportSummary]:
        rows = await self._session.scalars(
            select(ReportRow)
            .where(
                ReportRow.team_id == team_id,
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            )
            .order_by(ReportRow.created_at.desc(), ReportRow.id)
            .limit(limit)
        )
        return [
            TeamReportSummary(
                row.id, row.title, row.template, row.status, row.latest_version, row.created_at
            )
            for row in rows
        ]

    def _live_schedules(
        self, team_id: UUID, visibility: Visibility
    ) -> tuple[ColumnElement[bool], ...]:
        return (
            ScheduleRow.team_id == team_id,
            ScheduleRow.archived_at.is_(None),
            ScheduleRow.enabled.is_(True),
            visibility_predicate(ScheduleRow.created_by, ScheduleRow.team_id, visibility),
        )

    async def upcoming_runs(
        self, team_id: UUID, visibility: Visibility, limit: int
    ) -> list[TeamScheduledRun]:
        rows = await self._session.scalars(
            select(ScheduleRow)
            .where(*self._live_schedules(team_id, visibility))
            .order_by(ScheduleRow.next_run_at, ScheduleRow.id)
            .limit(limit)
        )
        return [TeamScheduledRun(row.id, row.name, row.cadence, row.next_run_at) for row in rows]

    async def action_items(
        self, team_id: UUID, visibility: Visibility, since: datetime, limit: int
    ) -> list[TeamActionItem]:
        """Up to ``limit`` orphaned schedules and ``limit`` unresolved failed editions."""
        # Scheduled team work stops when its owner leaves or is deactivated; a
        # Manager must create a reviewed replacement rather than inherit it.
        current_owner = and_(
            exists().where(
                TeamMembershipRow.team_id == team_id,
                TeamMembershipRow.user_id == ScheduleRow.created_by,
            ),
            exists().where(UserRow.id == ScheduleRow.created_by, UserRow.is_active.is_(True)),
        )
        orphaned = await self._session.scalars(
            select(ScheduleRow)
            .where(*self._live_schedules(team_id, visibility), not_(current_owner))
            .order_by(ScheduleRow.next_run_at, ScheduleRow.id)
            .limit(limit)
        )
        items = [
            TeamActionItem(TeamActionKind.OWNER_NOT_MEMBER, row.id, row.name, row.next_run_at)
            for row in orphaned
        ]
        later = aliased(SubscriptionEditionRow)
        resolved = exists().where(
            later.subscription_id == SubscriptionEditionRow.subscription_id,
            later.created_at > SubscriptionEditionRow.created_at,
            later.workflow == EditionWorkflow.COMPLETED.value,
        )
        editions = await self._session.execute(
            select(SubscriptionEditionRow, ScheduleRow.name)
            .join(ScheduleRow, ScheduleRow.id == SubscriptionEditionRow.subscription_id)
            .where(
                ScheduleRow.team_id == team_id,
                ScheduleRow.archived_at.is_(None),
                visibility_predicate(ScheduleRow.created_by, ScheduleRow.team_id, visibility),
                SubscriptionEditionRow.workflow.in_(tuple(_ATTENTION)),
                SubscriptionEditionRow.updated_at >= since,
                not_(resolved),
            )
            .order_by(SubscriptionEditionRow.updated_at.desc(), SubscriptionEditionRow.id)
            .limit(limit)
        )
        items.extend(
            TeamActionItem(
                _ATTENTION[edition.workflow],
                edition.subscription_id,
                name,
                edition.updated_at,
                edition.id,
            )
            for edition, name in editions
        )
        return items
