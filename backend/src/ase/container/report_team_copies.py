"""Composition for copying finished personal report versions into a team."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_team_copies import SqlReportTeamCopyRepository
from ase.application.reports.team_copies import ReportTeamCopies
from ase.container.core import ContainerCore


class ReportTeamCopyWiring(ContainerCore):
    def report_team_copies(self, session: AsyncSession) -> ReportTeamCopies:
        repos = self.repositories(session)
        return ReportTeamCopies(
            repos.reports,
            SqlReportTeamCopyRepository(session),
            repos.users,
            self.access_policy(session),
            self._auditor(repos),
            repos.uow,
            self.clock,
        )
