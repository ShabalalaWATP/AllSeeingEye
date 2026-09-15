"""SQL rows for team board posts, replies and per-membership read cursors."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class TeamBoardPostRow(Base):
    __tablename__ = "team_board_posts"
    __table_args__ = (
        CheckConstraint("length(text) BETWEEN 1 AND 4000", name="ck_board_text_length"),
        CheckConstraint("revision >= 1", name="ck_board_revision"),
        CheckConstraint(
            "removal IS NULL OR removal IN ('author', 'moderator')", name="ck_board_removal"
        ),
        # Mirrors migration 0048 exactly, including its composite listing indexes.
        Index("ix_team_board_posts_team", "team_id"),
        Index("ix_team_board_posts_author", "author_id"),
        Index("ix_team_board_posts_created", "team_id", "created_at"),
        Index("ix_team_board_posts_parent", "parent_id"),
        Index("ix_team_board_posts_pinned", "team_id", "is_pinned"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("teams.id", ondelete="CASCADE"))
    author_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("team_board_posts.id", ondelete="SET NULL"), nullable=True
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    removal: Mapped[str | None] = mapped_column(String(16), nullable=True)


class TeamBoardReadCursorRow(Base):
    __tablename__ = "team_board_read_cursors"

    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    membership_joined_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_read_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_read_post_id: Mapped[UUID] = mapped_column(Uuid)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
