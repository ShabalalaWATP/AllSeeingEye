"""Row to domain mapping shared by the AI usage policy store and ledger."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.ai_usage_models import (
    AiUsagePolicyOverrideRow,
    AiUsagePolicyRow,
    AiUsageReservationRow,
)
from ase.domain.ai_usage import (
    AiAllowancePeriod,
    AiPolicyScope,
    AiReservationStatus,
    AiUsagePolicy,
    AiUsageReservation,
)
from ase.domain.ai_usage_overrides import AiLimitOverride, AiLimitState, AiPolicyOverride


def rowcount(result: Any) -> int:
    """SQLAlchemy's async execute type hides rowcount although UPDATE returns it."""
    return int(cast(CursorResult[Any], result).rowcount or 0)


def dialect_insert(session: AsyncSession) -> Any:
    return pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert


def policy_from_row(row: AiUsagePolicyRow) -> AiUsagePolicy:
    return AiUsagePolicy(
        row.id,
        AiPolicyScope(row.scope),
        row.target_id,
        AiAllowancePeriod(row.period),
        row.request_limit,
        row.token_limit,
        row.enabled,
        row.revision,
        row.created_at,
        row.updated_at,
    )


def override_from_row(row: AiUsagePolicyOverrideRow) -> AiPolicyOverride:
    return AiPolicyOverride(
        row.id,
        row.policy_id,
        AiLimitOverride(AiLimitState(row.request_state), row.request_limit),
        AiLimitOverride(AiLimitState(row.token_state), row.token_limit),
        row.effective_from,
        row.expires_at,
        row.created_by,
        row.created_at,
        row.revoked_at,
    )


def reservation_from_row(row: AiUsageReservationRow) -> AiUsageReservation:
    return AiUsageReservation(
        row.id,
        row.call_id,
        row.policy_id,
        row.user_id,
        row.team_id,
        row.system,
        row.profile_id,
        row.model,
        row.purpose,
        row.period_start,
        row.period_end,
        row.reserved_tokens,
        AiReservationStatus(row.status),
        row.created_at,
        row.dispatched_at,
        row.settled_at,
        row.prompt_tokens,
        row.completion_tokens,
        row.actual_tokens,
        row.ok,
        row.error,
    )
