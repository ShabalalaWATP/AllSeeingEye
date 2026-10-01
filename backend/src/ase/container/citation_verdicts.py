"""Human citation verdicts: session-local service with no model or network dependencies."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.citation_verdicts import SqlCitationVerdictRepository
from ase.application.reports.citation_verdicts import CitationVerdicts
from ase.container.core import ContainerCore


class CitationVerdictWiring(ContainerCore):
    def citation_verdicts(self, session: AsyncSession) -> CitationVerdicts:
        r = self.repositories(session)
        return CitationVerdicts(
            r.users,
            r.refresh_tokens,
            r.reports,
            SqlCitationVerdictRepository(session),
            self.access_policy(session),
            self.clock,
            self._auditor(r),
            r.uow,
        )
