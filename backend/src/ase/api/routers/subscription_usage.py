"""Scoped read-only UTC-month usage for report subscriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ase.adapters.persistence.monthly_report_usage import monthly_usage
from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.session_fence import FenceDep
from ase.domain.errors import NotFound
from ase.domain.subscription_monthly_budget import MonthlyLimit, MonthlyUsage, utc_month

router = APIRouter(prefix="/schedules", tags=["schedules"])


class UsageCountsOut(BaseModel):
    requests: int
    output_tokens: int


class MonthlyUsageOut(BaseModel):
    scope: Literal["owner", "subscription"]
    subscription_id: UUID | None
    month_start: datetime
    month_end: datetime
    policy_version: str
    used: UsageCountsOut
    limit: UsageCountsOut


def _view(
    scope: Literal["owner", "subscription"],
    subscription_id: UUID | None,
    at: datetime,
    version: str,
    used: MonthlyUsage,
    limit: MonthlyLimit,
) -> MonthlyUsageOut:
    start, end = utc_month(at)
    return MonthlyUsageOut(
        scope=scope,
        subscription_id=subscription_id,
        month_start=start,
        month_end=end,
        policy_version=version,
        used=UsageCountsOut(requests=used.requests, output_tokens=used.output_tokens),
        limit=UsageCountsOut(requests=limit.requests, output_tokens=limit.output_tokens),
    )


@router.get("/usage")
async def owner_monthly_usage(
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> MonthlyUsageOut:
    at = container.clock.now()
    owner, _ = await monthly_usage(session, user.id, None, at)
    await fence.confirm(session=session)
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    policy = container.monthly_budget_policy
    return _view("owner", None, at, policy.version, owner, policy.owner)


@router.get("/{subscription_id}/usage")
async def subscription_monthly_usage(
    subscription_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> MonthlyUsageOut:
    access = await container.access_policy(session).context(user)
    schedule = await container.repositories(session).schedules.get(subscription_id)
    if schedule is None:
        raise NotFound("Subscription not found.")
    access.require_read(schedule.created_by, schedule.team_id)
    at = container.clock.now()
    _, subscription = await monthly_usage(session, schedule.created_by, subscription_id, at)
    await fence.confirm(session=session)
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    policy = container.monthly_budget_policy
    return _view(
        "subscription", subscription_id, at, policy.version, subscription, policy.subscription
    )
