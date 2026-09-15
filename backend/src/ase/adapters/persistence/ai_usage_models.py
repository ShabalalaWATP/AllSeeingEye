"""SQLAlchemy rows for the administrator controlled AI allowance ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class AiUsagePolicyRow(Base):
    __tablename__ = "ai_usage_policies"
    __table_args__ = (
        CheckConstraint("scope IN ('global','user','team')", name="ck_ai_policy_scope"),
        CheckConstraint("period IN ('day','week','month')", name="ck_ai_policy_period"),
        CheckConstraint(
            "request_limit IS NULL OR request_limit >= 0", name="ck_ai_policy_requests"
        ),
        CheckConstraint("token_limit IS NULL OR token_limit >= 0", name="ck_ai_policy_tokens"),
        CheckConstraint(
            "(scope = 'global' AND target_id IS NULL) OR "
            "(scope IN ('user','team') AND target_id IS NOT NULL)",
            name="ck_ai_policy_target",
        ),
        Index(
            "uq_ai_usage_policy_global",
            "scope",
            unique=True,
            sqlite_where=text("scope = 'global' AND enabled = 1"),
            postgresql_where=text("scope = 'global' AND enabled = true"),
        ),
        Index(
            "uq_ai_usage_policy_target",
            "scope",
            "target_id",
            unique=True,
            sqlite_where=text("scope <> 'global' AND enabled = 1"),
            postgresql_where=text("scope <> 'global' AND enabled = true"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope: Mapped[str] = mapped_column(String(12), index=True)
    target_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(8))
    request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AiUsageCounterRow(Base):
    """One mutable counter per policy window, updated under a database row lock."""

    __tablename__ = "ai_usage_counters"
    __table_args__ = (
        CheckConstraint("used_requests >= 0", name="ck_ai_counter_used_requests"),
        CheckConstraint("reserved_requests >= 0", name="ck_ai_counter_reserved_requests"),
        CheckConstraint("used_tokens >= 0", name="ck_ai_counter_used_tokens"),
        CheckConstraint("reserved_tokens >= 0", name="ck_ai_counter_reserved_tokens"),
    )

    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ai_usage_policies.id", ondelete="CASCADE"), primary_key=True
    )
    period_start: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    period_end: Mapped[datetime] = mapped_column(UTCDateTime)
    used_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    used_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reserved_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AiUsageReservationRow(Base):
    __tablename__ = "ai_usage_reservations"
    __table_args__ = (
        CheckConstraint("status IN ('reserved','settled')", name="ck_ai_reservation_status"),
        CheckConstraint("reserved_tokens >= 1", name="ck_ai_reservation_tokens"),
        CheckConstraint("actual_tokens IS NULL OR actual_tokens >= 0", name="ck_ai_actual_tokens"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ai_usage_policies.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    profile_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("llm_profiles.id"), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String(2048))
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    period_start: Mapped[datetime] = mapped_column(UTCDateTime)
    period_end: Mapped[datetime] = mapped_column(UTCDateTime)
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    settled_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(String(120), nullable=True)
