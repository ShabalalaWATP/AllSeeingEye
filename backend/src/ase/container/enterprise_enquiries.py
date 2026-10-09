"""Enquiry composition is isolated from account creation and authentication."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.enterprise_enquiries import SqlEnquiryRepository
from ase.application.enterprise_enquiries import SubmitEnquiry
from ase.container.core import ContainerCore


class EnquiryWiring(ContainerCore):
    def submit_enquiry(self, session: AsyncSession) -> SubmitEnquiry:
        repos = self.repositories(session)
        return SubmitEnquiry(
            SqlEnquiryRepository(session),
            self.operator_notices,
            self.limiter,
            self.clock,
            self._auditor(repos),
            repos.uow,
        )
