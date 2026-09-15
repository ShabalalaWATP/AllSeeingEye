"""SQL persistence for the opt-in operator directory and its bounded avatars."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    Uuid,
    and_,
    delete,
    func,
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, aliased, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.directory_avatar import DirectoryAvatar, ProcessedAvatar
from ase.domain.directory_profile import (
    DirectoryEntry,
    DirectoryField,
    DirectoryPage,
    DirectoryProfile,
)
from ase.domain.errors import UsernameTaken

# One boolean column per owner-selectable field keeps directory filtering portable SQL.
_VISIBILITY_COLUMNS = {field: f"show_{field.value}" for field in DirectoryField}


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
    show_job_title: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_organisation: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_biography: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_country: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_languages: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_expertise: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    show_timezone: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    avatar_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class DirectoryAvatarRow(Base):
    __tablename__ = "directory_avatars"
    __table_args__ = (
        CheckConstraint(
            "byte_count > 0 AND byte_count <= 262144", name="ck_directory_avatar_bytes"
        ),
        CheckConstraint(
            "width > 0 AND width <= 256 AND height > 0 AND height <= 256",
            name="ck_directory_avatar_dimensions",
        ),
        CheckConstraint(
            "content_type IN ('image/webp', 'image/png')", name="ck_directory_avatar_type"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    content_type: Mapped[str] = mapped_column(String(16))
    sha256: Mapped[str] = mapped_column(String(64))
    byte_count: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


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
        visible_fields=frozenset(
            field for field, column in _VISIBILITY_COLUMNS.items() if getattr(row, column)
        ),
        avatar_sha256=row.avatar_sha256,
        revision=row.revision,
        updated_at=row.updated_at,
    )


def _apply_profile(row: DirectoryProfileRow, profile: DirectoryProfile) -> None:
    values: dict[str, Any] = {
        "username": profile.username,
        "job_title": profile.job_title,
        "organisation": profile.organisation,
        "biography": profile.biography,
        "country": profile.country,
        "languages": list(profile.languages),
        "expertise": list(profile.expertise),
        "timezone": profile.timezone,
        "is_discoverable": profile.is_discoverable,
        "avatar_sha256": profile.avatar_sha256,
        "revision": profile.revision,
        "updated_at": profile.updated_at,
    }
    for field, column in _VISIBILITY_COLUMNS.items():
        values[column] = profile.shows(field)
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

    async def get_by_username(self, username: str) -> DirectoryProfile | None:
        row = await self._session.scalar(
            select(DirectoryProfileRow)
            .where(DirectoryProfileRow.username == username)
            .execution_options(populate_existing=True)
        )
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
        conditions = (
            UserRow.is_active.is_(True),
            DirectoryProfileRow.is_discoverable.is_(True),
            or_(
                func.lower(UserRow.display_name).like(pattern, escape="\\"),
                func.lower(DirectoryProfileRow.username).like(pattern, escape="\\"),
                # A hidden organisation must not be discoverable through matching either.
                and_(
                    DirectoryProfileRow.show_organisation.is_(True),
                    func.lower(DirectoryProfileRow.organisation).like(pattern, escape="\\"),
                ),
            ),
        )
        joined = select(DirectoryProfileRow.user_id).join(
            UserRow, UserRow.id == DirectoryProfileRow.user_id
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(joined.where(*conditions).subquery())
            )
            or 0
        )
        rows = await self._session.execute(
            select(DirectoryProfileRow, UserRow)
            .join(UserRow, UserRow.id == DirectoryProfileRow.user_id)
            .where(*conditions)
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

    async def get_avatar(self, user_id: UUID) -> DirectoryAvatar | None:
        row = await self._session.get(DirectoryAvatarRow, user_id, populate_existing=True)
        if row is None:
            return None
        return DirectoryAvatar(
            user_id=row.user_id,
            image=ProcessedAvatar(
                content=row.content,
                content_type=row.content_type,
                sha256=row.sha256,
                width=row.width,
                height=row.height,
            ),
            updated_at=row.updated_at,
        )

    async def save_avatar(self, avatar: DirectoryAvatar) -> None:
        row = await self._session.get(DirectoryAvatarRow, avatar.user_id)
        if row is None:
            row = DirectoryAvatarRow(user_id=avatar.user_id)
            self._session.add(row)
        image = avatar.image
        row.content = image.content
        row.content_type = image.content_type
        row.sha256 = image.sha256
        row.byte_count = len(image.content)
        row.width = image.width
        row.height = image.height
        row.updated_at = avatar.updated_at
        await self._session.flush()

    async def delete_avatar(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(DirectoryAvatarRow).where(DirectoryAvatarRow.user_id == user_id)
        )

    async def shares_team(self, viewer_id: UUID, target_id: UUID) -> bool:
        other = aliased(TeamMembershipRow)
        found = await self._session.scalar(
            select(TeamMembershipRow.team_id)
            .join(other, other.team_id == TeamMembershipRow.team_id)
            .where(TeamMembershipRow.user_id == viewer_id, other.user_id == target_id)
            .limit(1)
        )
        return found is not None
