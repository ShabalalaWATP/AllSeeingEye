"""Count settled usage receipts and retained reservations by UTC dispatch month."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import LlmUsageRow
from ase.adapters.persistence.report_job_codec import from_row
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.application.report_jobs.budget import (
    MAX_CALLS,
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
    rows = await session.execute(
        select(ReportJobRow, SubscriptionEditionRow.subscription_id)
        .outerjoin(SubscriptionEditionRow, SubscriptionEditionRow.job_id == ReportJobRow.id)
        .where(
            ReportJobRow.owner_id == owner_id,
            ReportJobRow.created_at < end,
            ReportJobRow.updated_at >= start,
        )
        .execution_options(populate_existing=True)
    )
    receipts = await session.scalars(
        select(LlmUsageRow.completion_tokens).where(
            LlmUsageRow.user_id == owner_id,
            LlmUsageRow.purpose == "report-job",
            LlmUsageRow.at >= start,
            LlmUsageRow.at < end,
        )
    )
    owner = MonthlyUsage()
    for completion_tokens in receipts:
        known = token_count(completion_tokens)
        if completion_tokens is not None and known is None:
            raise JobInterrupted()
        owner = owner.add(MonthlyUsage(1, known or 0))
    subscription = MonthlyUsage()
    for row, linked_subscription in rows:
        job = from_row(row)
        for call in _calls(job):
            dispatched, _ = utc_month(_call_month(call, job.created_at))
            if dispatched != start:
                continue
            charge = _call_usage(call)
            status = call["status"]
            if status in {"in_flight", "uncertain"}:
                owner = owner.add(charge)
            elif token_count(call.get("completion_tokens")) is None:
                # The settlement receipt retains the request. The linked payload
                # retains a full output reservation until usage is known.
                owner = owner.add(MonthlyUsage(0, charge.output_tokens))
            if subscription_id is not None and linked_subscription == subscription_id:
                subscription = subscription.add(charge)
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
