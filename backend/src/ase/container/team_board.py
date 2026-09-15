"""Team board, moderation and overview factories."""

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.team_dashboard import SqlTeamDashboardQueries
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.teams.board import TeamBoardService
from ase.application.teams.board_moderation import TeamBoardModerationService
from ase.application.teams.dashboard import TeamDashboardService

if TYPE_CHECKING:
    from ase.container import Container


class TeamBoardWiring:
    def team_board(self, session: AsyncSession) -> TeamBoardService:
        container = cast("Container", self)
        repos = container.repositories(session)
        return TeamBoardService(
            repos.team_board,
            SqlTeamRepository(session),
            repos.users,
            container.clock,
            container._auditor(repos),
            repos.uow,
        )

    def team_board_moderation(self, session: AsyncSession) -> TeamBoardModerationService:
        container = cast("Container", self)
        repos = container.repositories(session)
        return TeamBoardModerationService(
            repos.team_board,
            SqlTeamRepository(session),
            repos.users,
            container.clock,
            container._auditor(repos),
            repos.uow,
        )

    def team_dashboard(self, session: AsyncSession) -> TeamDashboardService:
        container = cast("Container", self)
        repos = container.repositories(session)
        return TeamDashboardService(
            container.access_policy(session),
            SqlTeamRepository(session),
            repos.team_board,
            self.team_board(session),
            SqlTeamDashboardQueries(session),
            container.clock,
        )
