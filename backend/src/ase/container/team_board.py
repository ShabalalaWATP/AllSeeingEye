"""Team board, moderation and overview factories."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.board_mentions import SqlBoardMentionRepository
from ase.adapters.persistence.map_workspace import SqlMapWorkspaceRepository
from ase.adapters.persistence.team_dashboard import SqlTeamDashboardQueries
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.bell.scope import BellSignals
from ase.application.teams.board import TeamBoardService
from ase.application.teams.board_mentions import BoardMentions
from ase.application.teams.board_moderation import TeamBoardModerationService
from ase.application.teams.board_subjects import BoardSubjects, ReportDiscussions
from ase.application.teams.dashboard import TeamDashboardService
from ase.container.core import ContainerCore


class TeamBoardWiring(ContainerCore):
    def board_mentions(self, session: AsyncSession) -> BoardMentions:
        return BoardMentions(
            SqlBoardMentionRepository(session), SqlTeamRepository(session), BellSignals(self.bus)
        )

    def board_subjects(self, session: AsyncSession) -> BoardSubjects:
        repos = self.repositories(session)
        return BoardSubjects(
            self.access_policy(session),
            repos.reports,
            repos.aois,
            SqlMapWorkspaceRepository(session),
        )

    def report_discussions(self, session: AsyncSession) -> ReportDiscussions:
        repos = self.repositories(session)
        return ReportDiscussions(self.access_policy(session), repos.reports, repos.team_board)

    def team_board(self, session: AsyncSession) -> TeamBoardService:
        repos = self.repositories(session)
        return TeamBoardService(
            repos.team_board,
            SqlTeamRepository(session),
            repos.users,
            self.clock,
            self._auditor(repos),
            repos.uow,
            self.board_subjects(session),
            self.board_mentions(session),
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
            self.board_mentions(session),
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
