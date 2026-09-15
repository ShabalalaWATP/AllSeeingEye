"""Append-only report ledger rows; current ordinal is an optimistic write gate."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ReportLedgerHeadRow(Base):
    __tablename__ = "report_ledger_heads"
    __table_args__ = (
        Index("ix_report_ledger_version", "report_version_id", "kind"),
        Index("ix_report_ledger_scope", "owner_id", "team_id"),
        CheckConstraint("kind IN ('forecast','indicator')", name="ck_report_ledger_kind"),
        CheckConstraint(
            "(kind = 'forecast' AND source_evidence_label IS NULL "
            "AND source_excerpt_sha256 IS NULL) "
            "OR (kind = 'indicator' AND source_evidence_label IS NOT NULL "
            "AND source_excerpt_sha256 IS NOT NULL)",
            name="ck_report_ledger_source_anchor",
        ),
        CheckConstraint("latest_ordinal BETWEEN 1 AND 512", name="ck_report_ledger_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id", ondelete="CASCADE"))
    report_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("report_versions.id", ondelete="CASCADE")
    )
    claim_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("claims.id", ondelete="CASCADE"))
    claim_revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("claim_revisions.id", ondelete="CASCADE")
    )
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"))
    source_evidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_excerpt_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_ordinal: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ReportLedgerEntryRow(Base):
    __tablename__ = "report_ledger_entries"
    __table_args__ = (
        Index("uq_report_ledger_entry_ordinal", "ledger_id", "ordinal", unique=True),
        CheckConstraint("ordinal BETWEEN 1 AND 512", name="ck_report_ledger_entry_ordinal"),
        CheckConstraint("payload_bytes BETWEEN 2 AND 16384", name="ck_report_ledger_entry_bytes"),
        CheckConstraint(
            "entry_kind IN ('forecast_version','forecast_decision',"
            "'indicator_version','indicator_reading')",
            name="ck_report_ledger_entry_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    ledger_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("report_ledger_heads.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    entry_kind: Mapped[str] = mapped_column(String(24))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_bytes: Mapped[int] = mapped_column(Integer)
