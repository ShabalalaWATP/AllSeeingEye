"""Composition for private brief, conversation and original-excerpt use cases."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.assistant_history import SqlAssistantHistory
from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork
from ase.adapters.persistence.brief_management import SqlBriefManagementRepository
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.application.assistant_history.manage import ManageAssistantHistory
from ase.application.reports.original_passages import ReadOriginalPassage
from ase.application.research.manage_briefs import ManageResearchBriefs

if TYPE_CHECKING:
    from ase.application.access import AccessPolicy
    from ase.application.ports.services import Clock
    from ase.application.ports.source_controls import SourceAdmission
    from ase.application.reports.access import GetReportUseCase


class PrivateRecordWiring:
    if TYPE_CHECKING:
        clock: Clock
        source_admission: SourceAdmission

        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...
        def get_report(self, session: AsyncSession) -> GetReportUseCase: ...

    def research_briefs(self, session: AsyncSession) -> ManageResearchBriefs:
        return ManageResearchBriefs(
            SqlBriefManagementRepository(session),
            self.access_policy(session),
            self.clock,
            SqlAlchemyUnitOfWork(session),
        )

    def original_passage_reader(self, session: AsyncSession) -> ReadOriginalPassage:
        return ReadOriginalPassage(
            SqlOriginalPassageRepository(session),
            self.get_report(session),
            self.source_admission,
            getattr(self, "original_source_policies", {}),
            self.clock,
        )

    def assistant_history(self, session: AsyncSession) -> ManageAssistantHistory:
        return ManageAssistantHistory(
            SqlAssistantHistory(session),
            self.get_report(session),
            self.clock,
            SqlAlchemyUnitOfWork(session),
        )
