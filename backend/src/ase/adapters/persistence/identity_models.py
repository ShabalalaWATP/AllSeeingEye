"""Identity roots retain exact report scope; revisions are append-only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class IdentityDecisionRow(Base):
    __tablename__ = "identity_decisions"
    __table_args__ = (
        UniqueConstraint(
            "report_version_id", "candidate_label", name="uq_identity_candidate_version"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id"), index=True)
    report_version_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report_versions.id"))
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), index=True)
    subject: Mapped[str] = mapped_column(String(4000))
    candidate_label: Mapped[str] = mapped_column(String(64))
    evidence_sha256: Mapped[str] = mapped_column(String(64))
    latest_revision_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class IdentityRevisionRow(Base):
    __tablename__ = "identity_decision_revisions"
    __table_args__ = (
        UniqueConstraint("decision_id", "number", name="uq_identity_revision_number"),
        CheckConstraint("number > 0", name="ck_identity_revision_number"),
        CheckConstraint("byte_size > 0", name="ck_identity_revision_bytes"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    decision_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("identity_decisions.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
