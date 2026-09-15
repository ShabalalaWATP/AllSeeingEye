"""Immutable, bounded canonical Research Brief revision rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.research_brief import MAX_BRIEF_BYTES


class ResearchBriefRevisionRow(Base):
    __tablename__ = "research_brief_revisions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_research_brief_revision"),
        CheckConstraint("schema_version = 1", name="ck_research_brief_schema"),
        CheckConstraint(
            f"payload_bytes BETWEEN 2 AND {MAX_BRIEF_BYTES}",
            name="ck_research_brief_payload_size",
        ),
        CheckConstraint("length(payload_sha256) = 64", name="ck_research_brief_digest_length"),
        CheckConstraint("origin IN ('authored','legacy-derived')", name="ck_research_brief_origin"),
        Index("ix_research_brief_owner_latest", "owner_id", "revised_at", "brief_id"),
        Index("ix_research_brief_team_latest", "team_id", "revised_at", "brief_id"),
    )

    brief_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(120))
    schema_version: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(20))
    published: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revised_at: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[str] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload_bytes: Mapped[int] = mapped_column(Integer)
