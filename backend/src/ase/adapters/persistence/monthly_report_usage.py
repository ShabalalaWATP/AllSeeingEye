"""Count settled usage receipts and retained reservations by UTC dispatch month."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import LlmUsageRow
from ase.adapters.persistence.report_job_usage_models import ReportJobUsageRow as UsageRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.application.report_jobs.budget import (
    MAX_CALLS,
    MAX_COUNTER,
    NOT_DISPATCHED_ERROR,
    JobInterrupted,
    token_count,
)
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_monthly_budget import (
    MonthlyBudgetPolicy,
    MonthlyUsage,
    require_monthly_room,
    utc_month,
)


def _call_month(call: dict[str, Any], created_at: datetime) -> datetime:
    stamp = call.get("dispatched_at")
    if stamp is None:
        # Historical calls predate dispatch stamps. Their frozen job admission is
        # the only retained timestamp; all new reservations carry an exact stamp.
        return created_at
    if type(stamp) is not str or len(stamp) > 40:
        raise JobInterrupted()
    try:
        value = datetime.fromisoformat(stamp)
        utc_month(value)
    except ValueError:
        raise JobInterrupted() from None
    return value


def _call_usage(call: dict[str, Any]) -> MonthlyUsage:
    reserved = token_count(call.get("reserved_output"))
    if reserved is None or not 1 <= reserved <= 256_000:
        raise JobInterrupted()
    status = call.get("status")
    if status not in {"in_flight", "completed", "failed", "uncertain"}:
        raise JobInterrupted()
    known = token_count(call.get("completion_tokens"))
    if status == "failed" and call.get("error") == NOT_DISPATCHED_ERROR and known == 0:
        # Released before dispatch: no provider request or output was spent.
        return MonthlyUsage(0, 0)
    output = known if status in {"completed", "failed"} and known is not None else reserved
    return MonthlyUsage(1, output)


def _calls(job: ReportJob) -> list[dict[str, Any]]:
    value = job.payload.get("calls", [])
    if (
        type(value) is not list
        or len(value) > MAX_CALLS
        or any(type(row) is not dict for row in value)
    ):
        raise JobInterrupted()
    return value


async def monthly_usage(
    session: AsyncSession,
    owner_id: UUID,
    subscription_id: UUID | None,
    at: datetime,
) -> tuple[MonthlyUsage, MonthlyUsage]:
    """Owner includes one-offs; subscriptions use their edition-linked job calls."""
    start, end = utc_month(at)
    receipt_count, receipt_tokens, invalid_receipts = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(LlmUsageRow.completion_tokens), 0),
                func.count().filter(
                    or_(
                        LlmUsageRow.completion_tokens < 0,
                        LlmUsageRow.completion_tokens > MAX_COUNTER,
                        LlmUsageRow.completion_tokens
                        != cast(LlmUsageRow.completion_tokens, Integer),
                    )
                ),
            ).where(
                LlmUsageRow.user_id == owner_id,
                LlmUsageRow.purpose == "report-job",
                LlmUsageRow.at >= start,
                LlmUsageRow.at < end,
            )
        )
    ).one()
    if invalid_receipts:
        raise JobInterrupted()
    pending_count, pending_tokens = (
        await session.execute(
            select(
                func.coalesce(func.sum(UsageRow.owner_requests), 0),
                func.coalesce(func.sum(UsageRow.owner_output_tokens), 0),
            ).where(
                UsageRow.owner_id == owner_id,
                UsageRow.month == start,
            )
        )
    ).one()
    owner = MonthlyUsage(int(receipt_count + pending_count), int(receipt_tokens + pending_tokens))
    subscription = MonthlyUsage()
    if subscription_id is not None:
        requests, tokens = (
            await session.execute(
                select(
                    func.coalesce(func.sum(UsageRow.subscription_requests), 0),
                    func.coalesce(func.sum(UsageRow.subscription_output_tokens), 0),
                )
                .join(SubscriptionEditionRow, SubscriptionEditionRow.job_id == UsageRow.job_id)
                .where(
                    UsageRow.owner_id == owner_id,
                    UsageRow.month == start,
                    SubscriptionEditionRow.subscription_id == subscription_id,
                )
            )
        ).one()
        subscription = MonthlyUsage(int(requests), int(tokens))

    return owner, subscription


async def require_admission_room(
    session: AsyncSession,
    owner_id: UUID,
    subscription_id: UUID | None,
    at: datetime,
    policy: MonthlyBudgetPolicy,
) -> None:
    owner, subscription = await monthly_usage(session, owner_id, subscription_id, at)
    require_monthly_room(owner, policy.owner, output_tokens=1)
    if subscription_id is not None:
        require_monthly_room(subscription, policy.subscription, output_tokens=1)


async def reserve_new_call(
    session: AsyncSession,
    job: ReportJob,
    payload: dict[str, Any],
    at: datetime,
    policy: MonthlyBudgetPolicy,
) -> None:
    """Stamp and authorise one append before its lease-fenced checkpoint commits."""
    old = _calls(job)
    new = payload.get("calls", [])
    if (
        type(new) is not list
        or len(new) > MAX_CALLS
        or len(new) < len(old)
        or len(new) > len(old) + 1
    ):
        raise JobInterrupted()
    if len(new) == len(old):
        return
    call = new[-1]
    if type(call) is not dict or "dispatched_at" in call:
        raise JobInterrupted()
    call["dispatched_at"] = at.isoformat()
    charge = _call_usage(call)
    subscription = await session.scalar(
        select(SubscriptionEditionRow.subscription_id).where(
            SubscriptionEditionRow.job_id == job.id
        )
    )
    owner_usage, subscription_usage = await monthly_usage(session, job.owner_id, subscription, at)
    require_monthly_room(owner_usage, policy.owner, output_tokens=charge.output_tokens)
    if subscription is not None:
        require_monthly_room(
            subscription_usage, policy.subscription, output_tokens=charge.output_tokens
        )
