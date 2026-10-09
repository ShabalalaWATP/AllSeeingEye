"""One activity timestamp per refresh family; rotation never changes this row."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import ForeignKey, SQLColumnExpression, Uuid, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.session_activity import SessionActivity, SessionIdlePolicy


class RefreshFamilyActivityRow(Base):
    __tablename__ = "refresh_family_activity"

    family_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    last_activity_at: Mapped[datetime] = mapped_column(UTCDateTime)


def active_activity(
    user_id: SQLColumnExpression[UUID] | UUID,
    family_id: SQLColumnExpression[UUID] | UUID,
    now: datetime,
    policy: SessionIdlePolicy,
) -> ColumnElement[bool]:
    from ase.adapters.persistence.models import UserRow  # noqa: PLC0415

    return exists().where(
        RefreshFamilyActivityRow.family_id == family_id,
        RefreshFamilyActivityRow.user_id == user_id,
        UserRow.id == RefreshFamilyActivityRow.user_id,
        (
            (UserRow.role == "admin")
            & (RefreshFamilyActivityRow.last_activity_at > now - policy.duration(is_admin=True))
        )
        | (
            (UserRow.role != "admin")
            & (RefreshFamilyActivityRow.last_activity_at > now - policy.duration(is_admin=False))
        ),
    )


async def read_activity(
    session: AsyncSession,
    user_id: UUID,
    family_id: UUID,
    now: datetime,
    policy: SessionIdlePolicy,
) -> SessionActivity | None:
    from ase.adapters.persistence.models import UserRow  # noqa: PLC0415

    row = (
        await session.execute(
            select(RefreshFamilyActivityRow.last_activity_at, UserRow.role).where(
                RefreshFamilyActivityRow.family_id == family_id,
                RefreshFamilyActivityRow.user_id == user_id,
                UserRow.id == RefreshFamilyActivityRow.user_id,
            )
        )
    ).first()
    if row is None:
        return None
    duration = policy.duration(is_admin=row.role == "admin")
    return SessionActivity(
        now,
        row.last_activity_at,
        row.last_activity_at + duration,
        int(duration.total_seconds() // 60),
    )


async def touch_activity(session: AsyncSession, family_id: UUID, now: datetime) -> bool:
    """Caller holds the account lock and has just checked the live family and deadline."""
    changed = await session.scalar(
        update(RefreshFamilyActivityRow)
        .where(
            RefreshFamilyActivityRow.family_id == family_id,
            RefreshFamilyActivityRow.last_activity_at <= now - timedelta(minutes=1),
        )
        .values(last_activity_at=now)
        .returning(RefreshFamilyActivityRow.family_id)
    )
    return changed is not None
