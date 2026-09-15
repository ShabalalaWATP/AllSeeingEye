"""Administrator-only subscription queue diagnostics."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from ase.adapters.persistence.subscription_diagnostics import subscription_diagnostics
from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, SessionDep
from ase.api.session_guard import validate_request_expiry, validate_request_session

router = APIRouter(prefix="/admin/subscriptions", tags=["admin"])


class SubscriptionDiagnosticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observed_at: datetime
    enabled_subscriptions: int
    overdue_subscriptions: int
    oldest_due_at: datetime | None
    oldest_due_lag_seconds: int | None
    active_editions_by_workflow: dict[str, int]
    uncertain_outcome_editions: int
    source_failure_editions: int
    source_failure_categories: dict[str, int]
    last_admitted_job_at: datetime | None
    open_report_jobs: int
    global_open_job_limit: int
    queue_saturated: bool


@router.get("/diagnostics")
async def get_subscription_diagnostics(
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionDiagnosticsOut:
    await validate_request_session(container, claims, admin_only=True)
    result = await subscription_diagnostics(session, now=container.clock.now())
    await validate_request_session(container, claims, admin_only=True)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionDiagnosticsOut.model_validate(result)
