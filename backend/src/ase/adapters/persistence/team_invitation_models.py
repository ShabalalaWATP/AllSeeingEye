"""SQLAlchemy rows for in-app team invitations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class TeamInvitationRow(Base):
    __tablename__ = "team_invitations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','declined','withdrawn','expired')",
            name="ck_team_invitation_status",
        ),
        CheckConstraint("role IN ('member','manager')", name="ck_team_invitation_role"),
        CheckConstraint("revision >= 1", name="ck_team_invitation_revision"),
        Index("ix_team_invitations_recipient_status", "recipient_id", "status"),
        Index("ix_team_invitations_team_status", "team_id", "status"),
        Index("ix_team_invitations_expires", "expires_at"),
        Index(
            "uq_team_invitations_pending_pair",
            "team_id",
            "recipient_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    recipient_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    inviter_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(280), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
