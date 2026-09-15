"""SQL rows for team board posts and replies."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class TeamBoardPostRow(Base):
    __tablename__ = "team_board_posts"
    __table_args__ = (
        CheckConstraint("length(text) BETWEEN 1 AND 4000", name="ck_board_text_length"),
        CheckConstraint("revision >= 1", name="ck_board_revision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("team_board_posts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
