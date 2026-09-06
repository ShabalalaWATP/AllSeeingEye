"""Private preferences stored separately from authentication state."""

from dataclasses import asdict
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base
from ase.domain.profile import PersonalProfile


class PersonalProfileRow(Base):
    __tablename__ = "personal_profiles"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON)


class SqlProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, display_name: str) -> PersonalProfile:
        row = await self._session.get(PersonalProfileRow, user_id, populate_existing=True)
        return PersonalProfile(display_name=display_name, **(row.preferences if row else {}))

    async def save(self, user_id: UUID, profile: PersonalProfile) -> None:
        # The use case holds the account lock, serialising insert/update per owner.
        row = await self._session.get(PersonalProfileRow, user_id)
        preferences = asdict(profile)
        del preferences["display_name"]
        if row is None:
            self._session.add(PersonalProfileRow(user_id=user_id, preferences=preferences))
        else:
            row.preferences = preferences
        await self._session.flush()
