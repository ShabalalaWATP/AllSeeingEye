"""A daily intent saves its exact interval, even when empty, cancelled or uncertain."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class DigestPreferenceRow(Base):
    __tablename__ = "notification_digest_preferences"
    __table_args__ = (
        CheckConstraint("hour BETWEEN 0 AND 23", name="ck_digest_hour"),
        Index("ix_digest_next_due", "enabled", "next_due_at"),
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(100))
    hour: Mapped[int] = mapped_column(Integer)
    cursor_at: Mapped[datetime] = mapped_column(UTCDateTime)
    next_due_at: Mapped[datetime] = mapped_column(UTCDateTime)


class DigestDeliveryRow(Base):
    __tablename__ = "notification_digest_outbox"
    __table_args__ = (
        UniqueConstraint("user_id", "local_day", name="uq_digest_user_day"),
        CheckConstraint("window_start < window_end", name="ck_digest_window"),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_digest_attempts"),
        Index("ix_digest_delivery_state", "state", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    local_day: Mapped[str] = mapped_column(String(10))
    timezone: Mapped[str] = mapped_column(String(100))
    window_start: Mapped[datetime] = mapped_column(UTCDateTime)
    window_end: Mapped[datetime] = mapped_column(UTCDateTime)
    state: Mapped[str] = mapped_column(String(20))
    attempts: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    safe_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
