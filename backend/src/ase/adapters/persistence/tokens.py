"""Refresh token and password token repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import exists, select, true, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import PasswordTokenRow, RefreshTokenRow
from ase.adapters.persistence.session_changes import mark_session_change
from ase.adapters.persistence.token_families import (
    family_is_revoked,
    prune_revoked_families,
    record_family_revocation,
    record_user_revocations,
)
from ase.domain.errors import NotFound
from ase.domain.tokens import PasswordToken, RefreshToken, TokenPurpose


def _refresh_from_row(row: RefreshTokenRow) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        family_id=row.family_id,
        parent_id=row.parent_id,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        ip=row.ip,
        user_agent=row.user_agent,
        mfa_verified=row.mfa_verified,
    )


class SqlRefreshTokenRepository:
    """Bulk revocations below are plain UPDATEs: rows already loaded in the same session are
    not refreshed, so callers must not rely on previously loaded token objects afterwards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def family_is_active(
        self, user_id: UUID, family_id: UUID, now: datetime, *, require_mfa: bool = False
    ) -> bool:
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        RefreshTokenRow.user_id == user_id,
                        RefreshTokenRow.family_id == family_id,
                        RefreshTokenRow.revoked_at.is_(None),
                        RefreshTokenRow.expires_at > now,
                        ~family_is_revoked(),
                        RefreshTokenRow.mfa_verified.is_(True) if require_mfa else true(),
                    )
                )
            )
        )

    async def add(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenRow(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                family_id=token.family_id,
                parent_id=token.parent_id,
                issued_at=token.issued_at,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
                ip=token.ip,
                user_agent=token.user_agent,
                mfa_verified=token.mfa_verified,
            )
        )
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
        row = (await self._session.scalars(stmt)).first()
        return _refresh_from_row(row) if row else None

    async def save(self, token: RefreshToken) -> None:
        row = await self._session.get(RefreshTokenRow, token.id)
        if row is None:
            raise NotFound()
        row.revoked_at = token.revoked_at
        row.expires_at = token.expires_at
        await self._session.flush()

    async def consume(self, token_id: UUID, now: datetime) -> bool:
        claimed = await self._session.scalar(
            update(RefreshTokenRow)
            .where(
                RefreshTokenRow.id == token_id,
                RefreshTokenRow.revoked_at.is_(None),
                RefreshTokenRow.expires_at > now,
                ~family_is_revoked(),
            )
            .values(revoked_at=now)
            .returning(RefreshTokenRow.id)
        )
        return claimed is not None

    async def revoke_family(self, family_id: UUID, now: datetime) -> int:
        await record_family_revocation(self._session, family_id, now)
        owner = await self._session.scalar(
            select(RefreshTokenRow.user_id).where(RefreshTokenRow.family_id == family_id).limit(1)
        )
        if owner is not None:
            mark_session_change(self._session, owner)
        stmt = (
            update(RefreshTokenRow)
            .where(RefreshTokenRow.family_id == family_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        await prune_revoked_families(self._session, now)
        return int(result.rowcount or 0)

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        await record_user_revocations(self._session, user_id, now)
        mark_session_change(self._session, user_id)
        stmt = (
            update(RefreshTokenRow)
            .where(RefreshTokenRow.user_id == user_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        await prune_revoked_families(self._session, now)
        return int(result.rowcount or 0)


def _password_token_from_row(row: PasswordTokenRow) -> PasswordToken:
    return PasswordToken(
        id=row.id,
        user_id=row.user_id,
        token_hash=row.token_hash,
        purpose=TokenPurpose(row.purpose),
        expires_at=row.expires_at,
        used_at=row.used_at,
        created_at=row.created_at,
    )


class SqlPasswordTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: PasswordToken) -> None:
        self._session.add(
            PasswordTokenRow(
                id=token.id,
                user_id=token.user_id,
                token_hash=token.token_hash,
                purpose=token.purpose.value,
                expires_at=token.expires_at,
                used_at=token.used_at,
                created_at=token.created_at,
            )
        )
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> PasswordToken | None:
        stmt = select(PasswordTokenRow).where(PasswordTokenRow.token_hash == token_hash)
        row = (await self._session.scalars(stmt)).first()
        return _password_token_from_row(row) if row else None

    async def save(self, token: PasswordToken) -> None:
        row = await self._session.get(PasswordTokenRow, token.id)
        if row is None:
            raise NotFound()
        row.used_at = token.used_at
        await self._session.flush()

    async def consume(self, token_id: UUID, now: datetime) -> bool:
        claimed = await self._session.scalar(
            update(PasswordTokenRow)
            .where(
                PasswordTokenRow.id == token_id,
                PasswordTokenRow.used_at.is_(None),
                PasswordTokenRow.expires_at > now,
            )
            .values(used_at=now)
            .returning(PasswordTokenRow.id)
        )
        return claimed is not None

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        """Mark every unused token as used so no outstanding link can be redeemed."""
        stmt = (
            update(PasswordTokenRow)
            .where(PasswordTokenRow.user_id == user_id, PasswordTokenRow.used_at.is_(None))
            .values(used_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return int(result.rowcount or 0)
