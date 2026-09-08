"""Bounded monitor checkpoints, append outbox and immutable transition manifests."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class AnnotationMonitorRow(Base):
    __tablename__ = "annotation_monitors"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(
        String(24), default="selected_roots", server_default="selected_roots"
    )
    inventory_overflow: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    name: Mapped[str] = mapped_column(String(120))
    categories: Mapped[list[str]] = mapped_column(JSON)
    notify_on_change: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(16), index=True)
    unavailable_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    revision: Mapped[int] = mapped_column(Integer)
    checkpoint_id: Mapped[UUID] = mapped_column(Uuid)
    checkpoint_number: Mapped[int] = mapped_column(Integer)
    checkpoint_payload: Mapped[str] = mapped_column(Text)
    checkpoint_sha256: Mapped[str] = mapped_column(String(64))
    checkpoint_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AnnotationWatchRow(Base):
    __tablename__ = "annotation_monitor_watches"
    monitor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("annotation_monitors.id"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    root_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True)
    revision_id: Mapped[UUID] = mapped_column(Uuid)


class AnnotationOutboxRow(Base):
    __tablename__ = "annotation_revision_outbox"
    __table_args__ = (
        UniqueConstraint("monitor_id", "revision_id", name="uq_annotation_outbox_delivery"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("annotation_monitors.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    root_id: Mapped[UUID] = mapped_column(Uuid)
    previous_revision_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    revision_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AnnotationTransitionRow(Base):
    __tablename__ = "annotation_monitor_transitions"
    __table_args__ = (
        UniqueConstraint("monitor_id", "sequence", name="uq_annotation_transition_sequence"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    monitor_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("annotation_monitors.id"), index=True)
    checkpoint_before: Mapped[UUID] = mapped_column(Uuid)
    checkpoint_after: Mapped[UUID] = mapped_column(Uuid, unique=True)
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime)
    changed_categories: Mapped[list[str]] = mapped_column(JSON)
    alert_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    configuration_revision: Mapped[int] = mapped_column(Integer)
    notification_categories: Mapped[list[str]] = mapped_column(JSON)
    notify_on_change: Mapped[bool] = mapped_column(Boolean)
    comparison_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
