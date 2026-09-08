"""Shared SEC client and session-scoped private filing workflow wiring."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.sec_client import SecClient
from ase.adapters.research_records.sec_provider import SecDocuments
from ase.adapters.research_records.sec_selections import BoundedSecSelections
from ase.application.access import AccessPolicy
from ase.application.ports import Clock, RateLimiter
from ase.application.ports.research_inputs import ResearchInputStore
from ase.application.ports.source_controls import SourceAdmission
from ase.application.research.sec_filings import SecFilings

if TYPE_CHECKING:
    from ase.container.repositories import Repositories


class SecFilingWiring:
    if TYPE_CHECKING:
        clock: Clock
        limiter: RateLimiter
        sec_client: SecClient
        sec_selections: BoundedSecSelections
        research_inputs: ResearchInputStore
        source_admission: SourceAdmission
        http: FeedHttpClient

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...

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
