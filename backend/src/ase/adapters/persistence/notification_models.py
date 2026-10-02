"""Opt-in notification settings and credentials, separate from account identity."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class PrivateFeedTokenRow(Base):
    __tablename__ = "private_feed_tokens"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    security_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    include_titles: Mapped[bool] = mapped_column(Boolean, default=False)


class NotificationPreferenceRow(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    include_names: Mapped[bool] = mapped_column(Boolean, default=False)


class SubscriptionNotificationRow(Base):
    __tablename__ = "subscription_notification_preferences"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("schedules.id"), primary_key=True
    )
    email_policy: Mapped[str] = mapped_column(String(24), default="none")
    attention: Mapped[bool] = mapped_column(Boolean, default=False)
