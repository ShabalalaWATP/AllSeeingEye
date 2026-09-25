"""Bounded session-family listing and durable bulk revocation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.base import UTCDateTime
from ase.adapters.persistence.models import RefreshTokenRow
from ase.adapters.persistence.session_changes import mark_session_change
from ase.adapters.persistence.token_families import RefreshFamilyRevocationRow, family_is_revoked
from ase.domain.session_summary import SessionPage, SessionSummary

SESSION_LIMIT = 100


class SqlAccountSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, user_id: UUID, current_family: UUID, now: datetime) -> SessionPage:
        # Rotations belong to one device session. Retain its original creation time,
        # while displaying only the latest live token's bounded client metadata.
        origins = (
            select(
                RefreshTokenRow.family_id,
                func.min(RefreshTokenRow.issued_at).label("created_at"),
            )
            .where(RefreshTokenRow.user_id == user_id)
            .group_by(RefreshTokenRow.family_id)
            .subquery()
        )
        live = (
            select(
                RefreshTokenRow.family_id,
                RefreshTokenRow.issued_at,
                RefreshTokenRow.expires_at,
                RefreshTokenRow.user_agent,
                RefreshTokenRow.ip,
                func.row_number()
                .over(
                    partition_by=RefreshTokenRow.family_id,
                    order_by=(RefreshTokenRow.issued_at.desc(), RefreshTokenRow.id.desc()),
                )
                .label("rank"),
            )
            .where(
                RefreshTokenRow.user_id == user_id,
                RefreshTokenRow.revoked_at.is_(None),
                RefreshTokenRow.expires_at > now,
                ~family_is_revoked(),
            )
            .subquery()
        )
        rows = (
            (
                await self._session.execute(
                    select(live, origins.c.created_at)
                    .join(origins, live.c.family_id == origins.c.family_id)
                    .where(live.c.rank == 1)
                    .order_by(
                        (live.c.family_id == current_family).desc(),
                        live.c.issued_at.desc(),
                        live.c.family_id,
                    )
                    .limit(SESSION_LIMIT + 1)
                )
            )
            .mappings()
            .all()
        )
        return SessionPage(
            items=[
                SessionSummary(
                    id=row["family_id"],
                    current=row["family_id"] == current_family,
                    created_at=row["created_at"],
                    last_active_at=row["issued_at"],
                    expires_at=row["expires_at"],
                    user_agent=row["user_agent"],
                    ip=row["ip"],
                )
                for row in rows[:SESSION_LIMIT]
            ],
            truncated=len(rows) > SESSION_LIMIT,
        )

    async def owns_family(self, user_id: UUID, family_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        RefreshTokenRow.user_id == user_id,
                        RefreshTokenRow.family_id == family_id,
                    )
                )
            )
        )

    async def revoke_others(self, user_id: UUID, current_family: UUID, now: datetime) -> None:
        mark_session_change(self._session, user_id)
        scope = (
            RefreshTokenRow.user_id == user_id,
            RefreshTokenRow.family_id != current_family,
        )
        families = (
            select(
                RefreshTokenRow.family_id,
                literal(now, type_=UTCDateTime),
            )
            .where(*scope)
            .distinct()
        )
        insert = (
            pg_insert if self._session.get_bind().dialect.name == "postgresql" else sqlite_insert
        )
        await self._session.execute(
            insert(RefreshFamilyRevocationRow)
            .from_select(["family_id", "revoked_at"], families)
            .on_conflict_do_nothing(index_elements=["family_id"])
        )
        await self._session.execute(
            update(RefreshTokenRow)
            .where(*scope, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
