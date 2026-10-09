"""Private enquiry rows and atomic duplicate suppression."""

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, Text, Uuid
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.enterprise_enquiries import EnterpriseEnquiry


class EnterpriseEnquiryRow(Base):
    __tablename__ = "enterprise_enquiries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))
    organisation: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(100))
    deployment_interest: Mapped[str] = mapped_column(String(20))
    expected_users: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    submission_key: Mapped[str] = mapped_column(String(64), unique=True)


class SqlEnquiryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_once(self, enquiry: EnterpriseEnquiry, submission_key: str) -> bool:
        # A first-write SQLite savepoint can escape the caller's outer rollback.
        # Direct DML owns no commit and ignores only the explicit duplicate key.
        insert = sqlite_insert if self.session.get_bind().dialect.name == "sqlite" else pg_insert
        statement = (
            insert(EnterpriseEnquiryRow)
            .values(
                id=enquiry.id,
                **asdict(enquiry.details),
                status=enquiry.status.value,
                created_at=enquiry.created_at,
                updated_at=enquiry.updated_at,
                submission_key=submission_key,
            )
            .on_conflict_do_nothing(index_elements=["submission_key"])
            .returning(EnterpriseEnquiryRow.id)
        )
        return await self.session.scalar(statement) is not None
