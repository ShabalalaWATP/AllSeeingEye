"""Append-only human citation verdicts, children of one exact saved report version."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class CitationVerdictRow(Base):
    __tablename__ = "citation_verdicts"
    __table_args__ = (
        Index("ix_citation_verdicts_version", "report_version_id", "recorded_at"),
        Index("ix_citation_verdicts_scope", "owner_id", "team_id"),
        Index("ix_citation_verdicts_recorded_at", "recorded_at"),
        CheckConstraint(
            "verdict IN ('supports','partly_supports','does_not_support','cannot_tell')",
            name="ck_citation_verdicts_verdict",
        ),
        CheckConstraint(
            "relation IN ('supporting','contradicting')", name="ck_citation_verdicts_relation"
        ),
        CheckConstraint(
            "note IS NULL OR length(note) BETWEEN 1 AND 300", name="ck_citation_verdicts_note"
        ),
        CheckConstraint("version_number >= 1", name="ck_citation_verdicts_version"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id", ondelete="CASCADE"))
    report_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("report_versions.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    judgement_id: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(200))
    relation: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    reviewer_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime)
