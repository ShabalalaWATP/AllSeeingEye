"""Enquiry composition is isolated from account creation and authentication."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.admin_enquiries import SqlAdminEnquiryRepository
from ase.adapters.persistence.enterprise_enquiries import SqlEnquiryRepository
from ase.application.admin.enquiries import AdminEnquiries
from ase.application.enterprise_enquiries import SubmitEnquiry
from ase.container.core import ContainerCore


class EnquiryWiring(ContainerCore):
    def admin_enquiries(self, session: AsyncSession) -> AdminEnquiries:
        repos = self.repositories(session)
        return AdminEnquiries(
            SqlAdminEnquiryRepository(session),
            repos.users,
            repos.refresh_tokens,
            self.clock,
            self._auditor(repos),
            repos.uow,
            self.settings.enterprise_enquiry_retention_days,
        )

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
