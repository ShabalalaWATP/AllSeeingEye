"""Frozen pre-projection computation from 69696286, used only as a parity oracle."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import LlmUsageRow
from ase.adapters.persistence.monthly_report_usage import _call_month, _call_usage, _calls
from ase.adapters.persistence.report_job_codec import from_row
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.application.report_jobs.budget import JobInterrupted, token_count
from ase.domain.subscription_monthly_budget import MonthlyUsage, utc_month


async def legacy_monthly_usage(
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
