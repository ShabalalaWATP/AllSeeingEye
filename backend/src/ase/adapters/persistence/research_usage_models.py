"""Small per-user counters survive deletion of reports and durable jobs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ResearchTierRow(Base):
    __tablename__ = "research_tiers"
    __table_args__ = (
        CheckConstraint("tier BETWEEN 1 AND 4", name="ck_research_tier"),
        CheckConstraint("revision > 0", name="ck_research_tier_revision"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    tier: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)


class ResearchUsageRow(Base):
    __tablename__ = "research_usage"
    __table_args__ = (
        CheckConstraint("period IN ('day', 'week')", name="ck_research_usage_period"),
        CheckConstraint("used >= 0", name="ck_research_usage_used"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    period: Mapped[str] = mapped_column(String(4), primary_key=True)
    period_start: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    used: Mapped[int] = mapped_column(Integer)
