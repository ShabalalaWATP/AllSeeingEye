"""SQL filtering and bounded deletion of private enquiry records."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.enterprise_enquiries import EnterpriseEnquiryRow as Row
from ase.domain.enterprise_enquiries import (
    DeploymentInterest,
    EnquiryDetails,
    EnquiryStatus,
    EnterpriseEnquiry,
    ExpectedUsers,
)


def _entity(row: Row) -> EnterpriseEnquiry:
    return EnterpriseEnquiry(
        row.id,
        EnquiryDetails(
            row.name,
            row.email,
            row.organisation,
            DeploymentInterest(row.deployment_interest),
            ExpectedUsers(row.expected_users),
            row.role,
            row.message,
        ),
        EnquiryStatus(row.status),
        row.created_at,
        row.updated_at,
    )


class SqlAdminEnquiryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self, cutoff: datetime, status: EnquiryStatus | None, limit: int, offset: int
    ) -> tuple[list[EnterpriseEnquiry], int]:
        predicates = [Row.created_at >= cutoff]
        if status is not None:
            predicates.append(Row.status == status.value)
        count = await self.session.scalar(select(func.count()).select_from(Row).where(*predicates))
        rows = await self.session.scalars(
            select(Row)
            .where(*predicates)
            .order_by(Row.created_at.desc(), Row.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_entity(row) for row in rows], count or 0

    async def get(self, enquiry_id: UUID, cutoff: datetime) -> EnterpriseEnquiry | None:
        row = await self.session.scalar(
            select(Row).where(Row.id == enquiry_id, Row.created_at >= cutoff)
        )
        return _entity(row) if row is not None else None

    async def set_status(self, enquiry_id: UUID, status: EnquiryStatus, now: datetime) -> None:
        await self.session.execute(
            update(Row).where(Row.id == enquiry_id).values(status=status.value, updated_at=now)
        )

    async def delete(self, enquiry_id: UUID) -> None:
        await self.session.execute(delete(Row).where(Row.id == enquiry_id))

    async def purge(self, cutoff: datetime, limit: int) -> int:
        ids = (
            select(Row.id)
            .where(Row.created_at < cutoff)
            .order_by(Row.created_at, Row.id)
            .limit(limit)
        )
        removed = await self.session.execute(
            delete(Row).where(Row.id.in_(ids)).execution_options(synchronize_session=False)
        )
        return cast(CursorResult[Any], removed).rowcount
