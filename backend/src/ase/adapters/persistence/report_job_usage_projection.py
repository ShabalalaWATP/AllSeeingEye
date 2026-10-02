"""Transaction-local projection of a validated checkpoint's bounded call ledger."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.monthly_report_usage import _call_month, _call_usage
from ase.adapters.persistence.report_job_usage_models import ReportJobUsageRow
from ase.application.report_jobs.budget import MAX_CALLS, JobInterrupted, token_count
from ase.domain.subscription_monthly_budget import utc_month


def usage_rows(
    job_id: UUID, owner_id: UUID, created_at: datetime, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    calls = payload.get("calls", [])
    if type(calls) is not list or len(calls) > MAX_CALLS:
        raise JobInterrupted()
    months: dict[datetime, dict[str, Any]] = {}
    for call in calls:
        if type(call) is not dict:
            raise JobInterrupted()
        month, _ = utc_month(_call_month(call, created_at))
        charge = _call_usage(call)
        row = months.setdefault(
            month,
            {
                "job_id": job_id,
                "owner_id": owner_id,
                "month": month,
                "owner_requests": 0,
                "owner_output_tokens": 0,
                "subscription_requests": 0,
                "subscription_output_tokens": 0,
            },
        )
        row["subscription_requests"] += charge.requests
        row["subscription_output_tokens"] += charge.output_tokens
        if call["status"] in {"in_flight", "uncertain"}:
            row["owner_requests"] += charge.requests
            row["owner_output_tokens"] += charge.output_tokens
        elif token_count(call.get("completion_tokens")) is None:
            row["owner_output_tokens"] += charge.output_tokens
    return list(months.values())


async def sync_usage(
    session: AsyncSession,
    job_id: UUID,
    owner_id: UUID,
    created_at: datetime,
    payload: dict[str, Any],
) -> None:
    rows = usage_rows(job_id, owner_id, created_at, payload)
    await session.execute(delete(ReportJobUsageRow).where(ReportJobUsageRow.job_id == job_id))
    if rows:
        await session.execute(insert(ReportJobUsageRow), rows)
