"""Shared SEC client and session-scoped private filing workflow wiring."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.research_records.sec_client import SecClient
from ase.adapters.research_records.sec_provider import SecDocuments
from ase.adapters.research_records.sec_selections import BoundedSecSelections
from ase.application.research.sec_filings import SecFilings
from ase.container.core import ContainerCore

if TYPE_CHECKING:
    pass


class SecFilingWiring(ContainerCore):
    def initialise_sec_filings(self) -> None:
        self.sec_client = SecClient(self.http)
        self.sec_selections = BoundedSecSelections(self.clock)

    def sec_filings(self, session: AsyncSession) -> SecFilings:
        repositories = self.repositories(session)
        return SecFilings(
            repositories.users,
            repositories.refresh_tokens,
            self.access_policy(session),
            self.clock,
            self.limiter,
            repositories.uow,
            SecDocuments(self.sec_client, self.clock),
            self.sec_selections,
            self.research_inputs,
            self.source_admission,
        )
