"""Permission-scoped, bounded metadata rows for selected subscriptions only."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class SelectedIndexGateRow(Base):
    """Singleton write gate; update it before aggregate quota checks and page writes."""

    __tablename__ = "selected_index_gate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)


class SelectedIndexCursorRow(Base):
    __tablename__ = "selected_index_cursors"
    __table_args__ = (CheckConstraint("revision >= 1", name="ck_selected_cursor_revision"),)

    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("schedules.id"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    revision: Mapped[int] = mapped_column(Integer)
    cursor_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    watermark_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_page_key: Mapped[str] = mapped_column(String(128))
    last_page_sha256: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class SelectedIndexRecordRow(Base):
    __tablename__ = "selected_index_records"
    __table_args__ = (
        UniqueConstraint("subscription_id", "fingerprint", name="uq_selected_record_fingerprint"),
        CheckConstraint("stored_bytes > 0", name="ck_selected_record_bytes"),
        Index("ix_selected_record_owner_age", "owner_id", "first_seen_at", "id"),
        Index("ix_selected_record_subscription_source", "subscription_id", "source_id", "id"),
        Index("ix_selected_record_origin", "subscription_id", "source_id", "origin_key", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("schedules.id"))
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String(100))
    item_key: Mapped[str] = mapped_column(String(200))
    origin_key: Mapped[str] = mapped_column(String(300))
    source_version: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(300))
    content_sha256: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    policy_id: Mapped[str] = mapped_column(String(100))
    retention_days: Mapped[int] = mapped_column(Integer)
    stored_bytes: Mapped[int] = mapped_column(Integer)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    corrects_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("selected_index_records.id", ondelete="SET NULL"), nullable=True
    )
    corrects_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SelectedIndexLossRow(Base):
    __tablename__ = "selected_index_losses"
    __table_args__ = (
        UniqueConstraint("subscription_id", "source_id", "reason", name="uq_selected_loss_scope"),
        Index("ix_selected_loss_subscription", "subscription_id", "source_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("schedules.id"))
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(24))
    lost_items: Mapped[int] = mapped_column(Integer)
    earliest_event_at: Mapped[datetime] = mapped_column(UTCDateTime)
    latest_event_at: Mapped[datetime] = mapped_column(UTCDateTime)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime)
