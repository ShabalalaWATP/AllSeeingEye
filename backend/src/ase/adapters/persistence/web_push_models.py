"""Encrypted browser endpoint credentials and an opaque per-device alert outbox."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class PushDeviceRow(Base):
    __tablename__ = "web_push_devices"
    __table_args__ = (
        Index("ix_push_user", "user_id"),
        Index("ix_push_family", "family_id"),
        Index("ix_push_next_check", "next_check_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    family_id: Mapped[UUID] = mapped_column(Uuid)
    security_version: Mapped[int] = mapped_column(Integer)
    endpoint_hash: Mapped[str] = mapped_column(String(64), unique=True)
    encrypted_subscription: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    next_check_at: Mapped[datetime] = mapped_column(UTCDateTime)


class PushDeliveryRow(Base):
    __tablename__ = "web_push_outbox"
    __table_args__ = (
        UniqueConstraint("device_id", "alert_id", name="uq_push_device_alert"),
        Index("ix_push_delivery_state", "state", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    device_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("web_push_devices.id", ondelete="CASCADE")
    )
    alert_id: Mapped[UUID] = mapped_column(Uuid)
    state: Mapped[str] = mapped_column(String(20))
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
