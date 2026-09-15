"""Single-row encrypted ACLED refresh token, so OAuth rotation survives restarts."""

from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.application.ports import Clock
from ase.application.ports.acled_credentials import StoredAcledRefreshToken


class AcledCredentialRow(Base):
    __tablename__ = "acled_credentials"
    __table_args__ = (CheckConstraint("id = 1", name="ck_acled_credentials_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    environment_fingerprint: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class SqlAcledCredentialStore:
    """Opens its own short sessions; the feed worker is not inside a request unit of work."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], clock: Clock) -> None:
        self._sessions, self._clock = sessions, clock

    async def load(self) -> StoredAcledRefreshToken | None:
        async with self._sessions() as session:
            row = await session.get(AcledCredentialRow, 1, populate_existing=True)
            if row is None:
                return None
            return StoredAcledRefreshToken(row.refresh_token_encrypted, row.environment_fingerprint)

    async def save(self, value: StoredAcledRefreshToken) -> None:
        async with self._sessions() as session:
            row = await session.get(AcledCredentialRow, 1)
            if row is None:
                row = AcledCredentialRow(id=1)
                session.add(row)
            row.refresh_token_encrypted = value.encrypted
            row.environment_fingerprint = value.environment_fingerprint
            row.updated_at = self._clock.now()
            await session.commit()
