"""Bounded team overview assembled from current authority."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports.services import Clock
from ase.application.ports.team_board import TeamBoardRepository
from ase.application.ports.team_dashboard import TeamDashboardQueries
from ase.application.ports.teams import TeamRepository
from ase.application.teams.board import TeamBoardService
from ase.application.teams.board_access import BoardActor
from ase.domain.errors import NotFound
from ase.domain.team_board import MAX_PINNED_POSTS
from ase.domain.team_dashboard import ACTION_LOOKBACK_DAYS, DASHBOARD_ITEM_LIMIT, TeamDashboard
from ase.domain.users import User


class TeamDashboardService:
    def __init__(
        self,
        access: AccessPolicy,
        teams: TeamRepository,
        board: TeamBoardRepository,
        board_service: TeamBoardService,
        queries: TeamDashboardQueries,
        clock: Clock,
    ) -> None:
        self._access = access
        self._teams = teams
        self._board = board
        self._board_service = board_service
        self._queries = queries
        self._clock = clock

    async def get(self, actor: User, team_id: UUID) -> TeamDashboard:
        context = await self._access.context(actor)
        team = context.teams.get(team_id)
        # Non-administrators only see teams they currently belong to.
        if team is None or (not context.actor.is_admin and team_id not in context.memberships):
            raise NotFound()
        membership = await self._teams.get_membership(team_id, context.actor.id)
        visibility = context.visibility
        limit = DASHBOARD_ITEM_LIMIT
        since = self._clock.now() - timedelta(days=ACTION_LOOKBACK_DAYS)
        return TeamDashboard(
            team=team,
            role=membership.role if membership else None,
            member_count=await self._teams.count_members(team_id),
            pinned=tuple(await self._board.pinned(team_id, MAX_PINNED_POSTS)),
            unread_count=await self._board_service.unread_for(
                BoardActor(context.actor, team, membership)
            ),
            recent_reports=tuple(await self._queries.recent_reports(team_id, visibility, limit)),
            upcoming_runs=tuple(await self._queries.upcoming_runs(team_id, visibility, limit)),
            action_items=tuple(await self._queries.action_items(team_id, visibility, since, limit)),
        )
