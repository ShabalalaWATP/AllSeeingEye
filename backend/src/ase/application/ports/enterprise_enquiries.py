"""Private enquiry persistence and configured operator-only notification ports."""

from typing import Protocol

from ase.domain.enterprise_enquiries import EnterpriseEnquiry


class EnquiryRepository(Protocol):
    async def add_once(self, enquiry: EnterpriseEnquiry, submission_key: str) -> bool:
        """Atomically add a submission, returning False for a duplicate key."""
        ...


class OperatorNoticeSender(Protocol):
    @property
    def available(self) -> bool: ...

    async def send_operator_notice(self, plain_text_body: str) -> bool:
        """Deliver to a configured operator address with a fixed subject, never a visitor."""
        ...
