"""Encrypted scoped endpoints and unique alert delivery intents, defaulting to no routing."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class AlertWebhookDestinationRow(Base):
    __tablename__ = "alert_webhook_destinations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    url_encrypted: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AlertRoutingRow(Base):
    __tablename__ = "alert_notification_routes"

    indicator_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("indicators.id", ondelete="CASCADE"), primary_key=True
    )
    configured_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    email_enabled: Mapped[bool] = mapped_column(Boolean)
    webhook_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("alert_webhook_destinations.id"), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer)


class AlertNotificationRow(Base):
    __tablename__ = "alert_notification_outbox"
    __table_args__ = (
        UniqueConstraint("alert_id", "channel", "destination_ref", name="uq_alert_delivery"),
        Index("ix_alert_delivery_pending", "state", "next_attempt_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    alert_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("alerts.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(24))
    destination_ref: Mapped[str] = mapped_column(String(64))
    route_revision: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    safe_reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
