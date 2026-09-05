"""Atomic TOTP state transitions for SQLite and PostgreSQL."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Uuid, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.totp import TotpState


class AdminTotpRow(Base):
    __tablename__ = "admin_totp"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    secret_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    pending_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    pending_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_step: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SqlTotpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> TotpState | None:
        row = await self._session.scalar(
            select(AdminTotpRow).where(AdminTotpRow.user_id == user_id)
        )
        return (
            TotpState(
                row.user_id,
                row.secret_encrypted,
                row.pending_encrypted,
                row.pending_expires_at,
                row.last_step,
            )
            if row
            else None
        )

    async def begin(self, user_id: UUID, encrypted: str, expires: datetime) -> bool:
        state = await self.get(user_id)
        if state is None:
            try:
                async with self._session.begin_nested():
                    self._session.add(
                        AdminTotpRow(
                            user_id=user_id,
                            pending_encrypted=encrypted,
                            pending_expires_at=expires,
                        )
                    )
                    await self._session.flush()
                return True
            except IntegrityError:
                return False
        changed = await self._session.scalar(
            update(AdminTotpRow)
            .where(
                AdminTotpRow.user_id == user_id,
                AdminTotpRow.secret_encrypted.is_(None),
            )
            .values(pending_encrypted=encrypted, pending_expires_at=expires)
            .returning(AdminTotpRow.user_id)
        )
        return changed is not None

    async def confirm(self, user_id: UUID, encrypted: str, step: int, now: datetime) -> bool:
        changed = await self._session.scalar(
            update(AdminTotpRow)
            .where(
                AdminTotpRow.user_id == user_id,
                AdminTotpRow.secret_encrypted.is_(None),
                AdminTotpRow.pending_encrypted == encrypted,
                AdminTotpRow.pending_expires_at > now,
            )
            .values(
                secret_encrypted=encrypted,
                pending_encrypted=None,
                pending_expires_at=None,
                last_step=step,
            )
            .returning(AdminTotpRow.user_id)
        )
        return changed is not None

    async def consume(self, user_id: UUID, encrypted: str, step: int) -> bool:
        changed = await self._session.scalar(
            update(AdminTotpRow)
            .where(
                AdminTotpRow.user_id == user_id,
                AdminTotpRow.secret_encrypted == encrypted,
                or_(AdminTotpRow.last_step.is_(None), AdminTotpRow.last_step < step),
            )
            .values(last_step=step)
            .returning(AdminTotpRow.user_id)
        )
        return changed is not None

    async def clear(self, user_id: UUID) -> None:
        await self._session.execute(
            update(AdminTotpRow)
            .where(AdminTotpRow.user_id == user_id)
            .values(
                secret_encrypted=None,
                pending_encrypted=None,
                pending_expires_at=None,
                last_step=None,
            )
        )
