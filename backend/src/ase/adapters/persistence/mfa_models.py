"""Persistent email factors and restricted second-factor challenges."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class EmailMfaRow(Base):
    __tablename__ = "email_mfa"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class MfaChallengeRow(Base):
    __tablename__ = "mfa_challenges"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    security_version: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    enrollment_required: Mapped[bool] = mapped_column(Boolean)
    attempts: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    code_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    pending_encrypted: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
