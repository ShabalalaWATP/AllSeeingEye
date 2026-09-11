"""Bounded durable report checkpoints and fenced worker leases."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ReportJobRow(Base):
    __tablename__ = "report_jobs"
    __table_args__ = (
        UniqueConstraint("owner_id", "request_key", name="uq_report_jobs_owner_request"),
        UniqueConstraint("version_id", name="uq_report_jobs_final_version"),
        CheckConstraint(
            "status IN ('queued','running','paused','completed','needs_review','failed')",
            name="ck_report_jobs_status",
        ),
        CheckConstraint("revision >= 1", name="ck_report_jobs_revision"),
        CheckConstraint("payload_bytes BETWEEN 2 AND 2097152", name="ck_report_jobs_payload_size"),
        CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
            "(status <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
            name="ck_report_jobs_lease",
        ),
        Index("ix_report_jobs_status_created", "status", "created_at", "id"),
        Index("ix_report_jobs_owner_created", "owner_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    request_key: Mapped[UUID] = mapped_column(Uuid)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20))
    stage: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revision: Mapped[int] = mapped_column(Integer)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_bytes: Mapped[int] = mapped_column(Integer)
    report_id: Mapped[UUID] = mapped_column(Uuid)
    version_id: Mapped[UUID] = mapped_column(Uuid)
    error: Mapped[str | None] = mapped_column(String(120), nullable=True)
