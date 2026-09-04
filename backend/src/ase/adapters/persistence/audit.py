"""Audit log repository and the unit of work."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AuditLogRow
from ase.domain.audit import AuditAction, AuditEntry


class SqlAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: AuditEntry) -> None:
        row = AuditLogRow(
            at=entry.at,
            actor_user_id=entry.actor_user_id,
            action=entry.action.value,
            subject=entry.subject,
            ip=entry.ip,
            details=dict(entry.details),
        )
        self._session.add(row)
        await self._session.flush()
        entry.id = row.id

    async def list_before(self, before: int | None, limit: int) -> list[AuditEntry]:
        stmt = select(AuditLogRow).order_by(AuditLogRow.id.desc()).limit(limit)
        if before is not None:
            stmt = stmt.where(AuditLogRow.id < before)
        rows = await self._session.scalars(stmt)
        return [
            AuditEntry(
                id=row.id,
                at=row.at,
                action=AuditAction(row.action),
                actor_user_id=row.actor_user_id,
                subject=row.subject,
                ip=row.ip,
                details=dict(row.details or {}),
            )
            for row in rows
        ]


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
