"""Encrypted singleton state; callers serialize writes through the administration lock."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, String, Text, Uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.firms_credentials import FirmsCredential


class FirmsCredentialRow(Base):
    __tablename__ = "firms_credentials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    active_revision: Mapped[int] = mapped_column(Integer)
    active_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    draft_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    test_generation: Mapped[int] = mapped_column(Integer)
    tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    tested_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tested_actor: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    tested_family: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    tested_security_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SqlFirmsCredentials:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> FirmsCredential:
        row = await self.session.get(FirmsCredentialRow, 1, populate_existing=True)
        if row is None:
            return FirmsCredential()
        return FirmsCredential(
            **{name: getattr(row, name) for name in FirmsCredential.__dataclass_fields__}
        )

    async def save(self, value: FirmsCredential) -> None:
        row = await self.session.get(FirmsCredentialRow, 1)
        if row is None:
            row = FirmsCredentialRow(id=1)
            self.session.add(row)
        for name in FirmsCredential.__dataclass_fields__:
            setattr(row, name, getattr(value, name))
        await self.session.flush()
