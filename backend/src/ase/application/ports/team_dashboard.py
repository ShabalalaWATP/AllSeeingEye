"""Read-only, bounded queries behind the team overview."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.team_dashboard import TeamActionItem, TeamReportSummary, TeamScheduledRun


class TeamDashboardQueries(Protocol):
    """Every query filters by the team and the caller's visibility before its limit."""

    async def recent_reports(
        self, team_id: UUID, visibility: Visibility, limit: int
    ) -> list[TeamReportSummary]: ...

    async def upcoming_runs(
        self, team_id: UUID, visibility: Visibility, limit: int
    ) -> list[TeamScheduledRun]: ...

    async def action_items(
        self, team_id: UUID, visibility: Visibility, since: datetime, limit: int
    ) -> list[TeamActionItem]: ...
