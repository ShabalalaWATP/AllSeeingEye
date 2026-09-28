"""Team board, moderation and overview factories."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.team_dashboard import SqlTeamDashboardQueries
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.teams.board import TeamBoardService
from ase.application.teams.board_moderation import TeamBoardModerationService
from ase.application.teams.dashboard import TeamDashboardService
from ase.container.core import ContainerCore


class TeamBoardWiring(ContainerCore):
    def team_board(self, session: AsyncSession) -> TeamBoardService:
        repos = self.repositories(session)
        return TeamBoardService(
            repos.team_board,
            SqlTeamRepository(session),
            repos.users,
            self.clock,
            self._auditor(repos),
            repos.uow,
        )

    def team_board_moderation(self, session: AsyncSession) -> TeamBoardModerationService:
        repos = self.repositories(session)
        return TeamBoardModerationService(
            repos.team_board,
            SqlTeamRepository(session),
            repos.users,
            self.clock,
            self._auditor(repos),
            repos.uow,
        )

    def team_dashboard(self, session: AsyncSession) -> TeamDashboardService:
        repos = self.repositories(session)
        return TeamDashboardService(
            self.access_policy(session),
            SqlTeamRepository(session),
            repos.team_board,
            self.team_board(session),
            SqlTeamDashboardQueries(session),
            self.clock,
        )
