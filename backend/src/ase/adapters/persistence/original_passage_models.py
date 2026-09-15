"""Selected public excerpts only, with current-access and physical expiry boundaries."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class OriginalPassageRow(Base):
    __tablename__ = "original_passage_assets"
    __table_args__ = (
        CheckConstraint("length(document_version_id) = 64", name="ck_original_passage_version"),
        CheckConstraint("length(passage_id) = 64", name="ck_original_passage_digest"),
        Index("ix_original_passage_job_event", "job_id", "event_id", unique=True),
        Index("ix_original_passage_expiry", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    job_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report_jobs.id", ondelete="CASCADE"))
    report_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    source_id: Mapped[str] = mapped_column(String(120))
    event_id: Mapped[str] = mapped_column(String(256))
    evidence_label: Mapped[str] = mapped_column(String(16))
    candidate_id: Mapped[str] = mapped_column(String(64))
    document_version_id: Mapped[str] = mapped_column(String(64))
    passage_id: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
