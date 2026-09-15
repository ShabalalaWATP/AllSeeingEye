"""SQL persistence for the opt-in operator directory."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.models import UserRow
from ase.domain.directory_profile import DirectoryEntry, DirectoryPage, DirectoryProfile
from ase.domain.errors import UsernameTaken


class DirectoryProfileRow(Base):
    __tablename__ = "directory_profiles"
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_directory_profile_revision"),
        CheckConstraint(
            "country IS NULL OR length(country) = 2", name="ck_directory_profile_country"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    username: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    organisation: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    expertise: Mapped[list[str]] = mapped_column(JSON, default=list)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_discoverable: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", index=True
    )
    show_timezone: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


def _profile_from_row(row: DirectoryProfileRow) -> DirectoryProfile:
    return DirectoryProfile(
        user_id=row.user_id,
        username=row.username,
        job_title=row.job_title,
        organisation=row.organisation,
        biography=row.biography,
        country=row.country,
        languages=tuple(row.languages or ()),
        expertise=tuple(row.expertise or ()),
        timezone=row.timezone,
        is_discoverable=row.is_discoverable,
        show_timezone=row.show_timezone,
        revision=row.revision,
        updated_at=row.updated_at,
    )


def _apply_profile(row: DirectoryProfileRow, profile: DirectoryProfile) -> None:
    values = asdict(profile)
    values["languages"] = list(profile.languages)
    values["expertise"] = list(profile.expertise)
    values.pop("user_id")
    for key, value in values.items():
        setattr(row, key, value)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlDirectoryProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> DirectoryProfile | None:
        row = await self._session.get(DirectoryProfileRow, user_id, populate_existing=True)
        return _profile_from_row(row) if row else None

    async def save(self, profile: DirectoryProfile) -> None:
        row = await self._session.get(DirectoryProfileRow, profile.user_id)
        if row is None:
            row = DirectoryProfileRow(user_id=profile.user_id)
            _apply_profile(row, profile)
            self._session.add(row)
        else:
            _apply_profile(row, profile)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Do not surface database constraint text, which can disclose schema details.
            if "username" in str(exc.orig).lower():
                raise UsernameTaken() from None
            raise

    async def search(self, query: str, limit: int, offset: int) -> DirectoryPage:
        pattern = f"%{_escape_like(query.casefold())}%"
        base = (
            select(DirectoryProfileRow.user_id)
            .join(UserRow, UserRow.id == DirectoryProfileRow.user_id)
            .where(
                UserRow.is_active.is_(True),
                DirectoryProfileRow.is_discoverable.is_(True),
                or_(
                    func.lower(UserRow.display_name).like(pattern, escape="\\"),
                    func.lower(DirectoryProfileRow.username).like(pattern, escape="\\"),
                    func.lower(DirectoryProfileRow.organisation).like(pattern, escape="\\"),
                ),
            )
        )
        total = int(
            await self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        rows = await self._session.execute(
            select(DirectoryProfileRow, UserRow)
            .join(UserRow, UserRow.id == DirectoryProfileRow.user_id)
            .where(
                UserRow.is_active.is_(True),
                DirectoryProfileRow.is_discoverable.is_(True),
                or_(
                    func.lower(UserRow.display_name).like(pattern, escape="\\"),
                    func.lower(DirectoryProfileRow.username).like(pattern, escape="\\"),
                    func.lower(DirectoryProfileRow.organisation).like(pattern, escape="\\"),
                ),
            )
            .order_by(UserRow.display_name, DirectoryProfileRow.username, UserRow.id)
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        )
        items = tuple(
            DirectoryEntry(profile=_profile_from_row(profile), display_name=user.display_name)
            for profile, user in rows.all()
        )
        return DirectoryPage(items=items, total=total, offset=offset, limit=limit)
