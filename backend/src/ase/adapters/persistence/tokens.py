"""Refresh token and password token repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import PasswordTokenRow, RefreshTokenRow
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
    )


class SqlRefreshTokenRepository:
    """Bulk revocations below are plain UPDATEs: rows already loaded in the same session are
    not refreshed, so callers must not rely on previously loaded token objects afterwards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

    async def revoke_family(self, family_id: UUID, now: datetime) -> int:
        stmt = (
            update(RefreshTokenRow)
            .where(RefreshTokenRow.family_id == family_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return int(result.rowcount or 0)

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        stmt = (
            update(RefreshTokenRow)
            .where(RefreshTokenRow.user_id == user_id, RefreshTokenRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
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

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        """Mark every unused token as used so no outstanding link can be redeemed."""
        stmt = (
            update(PasswordTokenRow)
            .where(PasswordTokenRow.user_id == user_id, PasswordTokenRow.used_at.is_(None))
            .values(used_at=now)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return int(result.rowcount or 0)
