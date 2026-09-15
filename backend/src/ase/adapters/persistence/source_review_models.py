"""Scoped append-only review history and exact-report child snapshots."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class SourceReviewHeadRow(Base):
    __tablename__ = "source_review_heads"
    __table_args__ = (
        Index("ix_source_review_owner", "owner_id", "team_id"),
        CheckConstraint(
            "kind IN ('reliability','credibility','authenticity')", name="ck_source_review_kind"
        ),
    )
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"))
    kind: Mapped[str] = mapped_column(String(20))
    latest_id: Mapped[UUID] = mapped_column(Uuid)


class SourceReviewRevisionRow(Base):
    __tablename__ = "source_review_revisions"
    __table_args__ = (
        Index("uq_source_review_number", "head_key", "number", unique=True),
        CheckConstraint("number BETWEEN 1 AND 100", name="ck_source_review_number"),
        CheckConstraint("payload_bytes BETWEEN 2 AND 16384", name="ck_source_review_bytes"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    head_key: Mapped[str] = mapped_column(String(64), ForeignKey("source_review_heads.key"))
    number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_bytes: Mapped[int] = mapped_column(Integer)


class SourceReviewSnapshotRow(Base):
    __tablename__ = "source_review_snapshots"
    __table_args__ = (
        Index("ix_source_review_snapshot_version", "report_version_id"),
        CheckConstraint("payload_bytes BETWEEN 2 AND 4194304", name="ck_source_snapshot_bytes"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id", ondelete="CASCADE"))
    report_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("report_versions.id", ondelete="CASCADE")
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_bytes: Mapped[int] = mapped_column(Integer)
