"""Private enquiry persistence and configured operator-only notification ports."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.enterprise_enquiries import EnquiryStatus, EnterpriseEnquiry


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


class AdminEnquiryRepository(Protocol):
    async def list(
        self, cutoff: datetime, status: EnquiryStatus | None, limit: int, offset: int
    ) -> tuple[list[EnterpriseEnquiry], int]: ...

    async def get(self, enquiry_id: UUID, cutoff: datetime) -> EnterpriseEnquiry | None: ...

    async def set_status(self, enquiry_id: UUID, status: EnquiryStatus, now: datetime) -> None: ...

    async def delete(self, enquiry_id: UUID) -> None: ...

    async def purge(self, cutoff: datetime, limit: int) -> int: ...
