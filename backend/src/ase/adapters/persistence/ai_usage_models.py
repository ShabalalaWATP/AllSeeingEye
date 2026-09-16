"""SQLAlchemy rows for the administrator controlled AI allowance ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime

# Totals use this key for "no team" and "no account" so the composite key stays non-null.
NIL_KEY = UUID(int=0)
LIMIT_STATES = "('inherit','limit','unlimited','blocked')"


class AiUsagePolicyRow(Base):
    __tablename__ = "ai_usage_policies"
    __table_args__ = (
        CheckConstraint("scope IN ('global','system','user','team')", name="ck_ai_policy_scope"),
        CheckConstraint("period IN ('day','week','month')", name="ck_ai_policy_period"),
        CheckConstraint(
            "request_limit IS NULL OR request_limit >= 0", name="ck_ai_policy_requests"
        ),
        CheckConstraint("token_limit IS NULL OR token_limit >= 0", name="ck_ai_policy_tokens"),
        CheckConstraint(
            "(scope IN ('global','system') AND target_id IS NULL) OR "
            "(scope IN ('user','team') AND target_id IS NOT NULL)",
            name="ck_ai_policy_target",
        ),
        Index(
            "uq_ai_usage_policy_global",
            "scope",
            "period",
            unique=True,
            sqlite_where=text("scope IN ('global','system') AND enabled = 1"),
            postgresql_where=text("scope IN ('global','system') AND enabled = true"),
        ),
        Index(
            "uq_ai_usage_policy_target",
            "scope",
            "target_id",
            "period",
            unique=True,
            sqlite_where=text("scope IN ('user','team') AND enabled = 1"),
            postgresql_where=text("scope IN ('user','team') AND enabled = true"),
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


class AiUsagePolicyOverrideRow(Base):
    """A dated override; only revocation changes a row after creation."""

    __tablename__ = "ai_usage_policy_overrides"
    __table_args__ = (
        CheckConstraint(f"request_state IN {LIMIT_STATES}", name="ck_ai_override_request_state"),
        CheckConstraint(f"token_state IN {LIMIT_STATES}", name="ck_ai_override_token_state"),
        CheckConstraint(
            "(request_state = 'limit' AND request_limit IS NOT NULL AND request_limit >= 0) OR "
            "(request_state <> 'limit' AND request_limit IS NULL)",
            name="ck_ai_override_request_limit",
        ),
        CheckConstraint(
            "(token_state = 'limit' AND token_limit IS NOT NULL AND token_limit >= 0) OR "
            "(token_state <> 'limit' AND token_limit IS NULL)",
            name="ck_ai_override_token_limit",
        ),
        CheckConstraint("expires_at > effective_from", name="ck_ai_override_window"),
        Index("ix_ai_usage_overrides_policy_window", "policy_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ai_usage_policies.id", ondelete="CASCADE")
    )
    request_state: Mapped[str] = mapped_column(String(12))
    request_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_state: Mapped[str] = mapped_column(String(12))
    token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effective_from: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class AiUsageCounterRow(Base):
    """One mutable counter per policy window, changed only by relative conditional updates."""

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


class AiUsageTotalRow(Base):
    """Bounded monthly observation per account, account-within-team or system bucket."""

    __tablename__ = "ai_usage_totals"
    __table_args__ = (
        CheckConstraint("used_requests >= 0", name="ck_ai_total_used_requests"),
        CheckConstraint("used_tokens >= 0", name="ck_ai_total_used_tokens"),
        CheckConstraint("used_input_tokens >= 0", name="ck_ai_total_input_tokens"),
        CheckConstraint("used_output_tokens >= 0", name="ck_ai_total_output_tokens"),
        CheckConstraint("unknown_requests >= 0", name="ck_ai_total_unknown_requests"),
    )

    period_start: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    team_key: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_key: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    period_end: Mapped[datetime] = mapped_column(UTCDateTime)
    used_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    used_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # The split always sums to used_tokens: a charge the provider did not split is
    # counted as output, the dearer rate, so a spend estimate never understates.
    used_input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    used_output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    unknown_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AiUsageReservationRow(Base):
    """One row per applicable policy for a provider call; ``call_id`` groups them."""

    __tablename__ = "ai_usage_reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved','settled','released','unknown')",
            name="ck_ai_reservation_status",
        ),
        CheckConstraint("reserved_tokens >= 1", name="ck_ai_reservation_tokens"),
        CheckConstraint("actual_tokens IS NULL OR actual_tokens >= 0", name="ck_ai_actual_tokens"),
        CheckConstraint(
            "(system = true AND user_id IS NULL AND team_id IS NULL) OR "
            "(system = false AND user_id IS NOT NULL)",
            name="ck_ai_reservation_attribution",
        ),
        Index("ix_ai_usage_reservations_status_created", "status", "created_at"),
        Index("ix_ai_usage_reservations_status_period_end", "status", "period_end"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    call_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ai_usage_policies.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True, index=True
    )
    team_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    profile_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("llm_profiles.id"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(2048))
    purpose: Mapped[str] = mapped_column(String(64))
    period_start: Mapped[datetime] = mapped_column(UTCDateTime)
    period_end: Mapped[datetime] = mapped_column(UTCDateTime)
    reserved_tokens: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(String(120), nullable=True)
