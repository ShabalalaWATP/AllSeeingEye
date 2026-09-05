"""Durable family invalidation, including descendants outside an UPDATE snapshot."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Uuid, delete, exists, literal, select
from sqlalchemy.dialects.postgresql import Insert as PostgresInsert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import Insert as SqliteInsert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.selectable import Exists

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.models import RefreshTokenRow

# Settings cap a refresh lifetime at 90 days. Keep an additional day before
# collecting expired revoked families, and retain any family with a live token.
REVOCATION_RETENTION = timedelta(days=91)


class RefreshFamilyRevocationRow(Base):
    __tablename__ = "refresh_family_revocations"

    family_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    revoked_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


def family_is_revoked() -> Exists:
    """A correlated predicate usable within atomic refresh-token consumption."""
    return exists().where(RefreshFamilyRevocationRow.family_id == RefreshTokenRow.family_id)


def _insert(session: AsyncSession) -> PostgresInsert | SqliteInsert:
    if session.get_bind().dialect.name == "postgresql":
        return pg_insert(RefreshFamilyRevocationRow)
    return sqlite_insert(RefreshFamilyRevocationRow)


async def record_family_revocation(session: AsyncSession, family_id: UUID, now: datetime) -> None:
    await session.execute(
        _insert(session)
        .values(family_id=family_id, revoked_at=now)
        .on_conflict_do_nothing(index_elements=["family_id"])
    )


async def record_user_revocations(session: AsyncSession, user_id: UUID, now: datetime) -> None:
    families = (
        select(RefreshTokenRow.family_id, literal(now, type_=UTCDateTime))
        .where(
            RefreshTokenRow.user_id == user_id,
        )
        .distinct()
    )
    await session.execute(
        _insert(session)
        .from_select(["family_id", "revoked_at"], families)
        .on_conflict_do_nothing(index_elements=["family_id"])
    )


async def prune_revoked_families(session: AsyncSession, now: datetime) -> None:
    old_families = select(RefreshFamilyRevocationRow.family_id).where(
        RefreshFamilyRevocationRow.revoked_at <= now - REVOCATION_RETENTION,
    )
    await session.execute(
        delete(RefreshTokenRow).where(
            RefreshTokenRow.family_id.in_(old_families),
            RefreshTokenRow.expires_at <= now,
        )
    )
    await session.execute(
        delete(RefreshFamilyRevocationRow).where(
            RefreshFamilyRevocationRow.revoked_at <= now - REVOCATION_RETENTION,
            ~exists().where(RefreshTokenRow.family_id == RefreshFamilyRevocationRow.family_id),
        )
    )
