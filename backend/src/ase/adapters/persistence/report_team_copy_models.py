"""SQL row for the provenance of a team copy of one personal report version."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
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


class ReportTeamCopyRow(Base):
    __tablename__ = "report_team_copies"
    __table_args__ = (
        # Mirrors migration 0078: one copy per source version and team, so a retry or a
        # concurrent request cannot publish the same version twice.
        UniqueConstraint("source_version_id", "team_id", name="uq_report_team_copy_source"),
        UniqueConstraint("report_id", name="uq_report_team_copy_report"),
        CheckConstraint("source_version_number >= 1", name="ck_report_team_copy_version"),
        Index("ix_report_team_copies_source", "source_report_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=False)
    # Provenance only, without a foreign key: the personal original may later be deleted
    # by its owner while the team keeps its copy.
    source_report_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    copied_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    copied_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    disclosed_labels: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    omissions: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
