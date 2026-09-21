"""Job-less subscription admission waits and bounded recovery checks."""

from dataclasses import replace
from datetime import datetime, timedelta

from ase.application.report_jobs.controls import ReportJobCapacity
from ase.domain.errors import RateLimited
from ase.domain.research_usage import ResearchUsageLimit
from ase.domain.subscription_editions import EditionWorkflow, SubscriptionEdition
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted

BUDGET_BLOCK_REASON = "monthly_budget_exhausted"
BUDGET_RETRY_AFTER = timedelta(hours=1)
RESEARCH_BLOCK_REASON = "research_usage_limit"
RESEARCH_RETRY_AFTER = timedelta(minutes=5)


def admission_wait(
    edition: SubscriptionEdition,
    now: datetime,
    error: MonthlyBudgetExhausted | RateLimited | ReportJobCapacity,
) -> SubscriptionEdition:
    # ResearchUsageLimit extends RateLimited, so classify it before capacity waits.
    reason = (
        RESEARCH_BLOCK_REASON
        if isinstance(error, ResearchUsageLimit)
        else BUDGET_BLOCK_REASON
        if isinstance(error, MonthlyBudgetExhausted)
        else "capacity_wait"
    )
    return replace(
        edition,
        workflow=EditionWorkflow.PENDING if reason == "capacity_wait" else EditionWorkflow.BLOCKED,
        safe_reason=reason,
        updated_at=now,
        revision=edition.revision + 1,
    )


def admission_retry_due(edition: SubscriptionEdition, now: datetime) -> bool:
    """Probe quota changes at a bounded interval so upgrades need no manual recovery."""
    delay = {
        BUDGET_BLOCK_REASON: BUDGET_RETRY_AFTER,
        RESEARCH_BLOCK_REASON: RESEARCH_RETRY_AFTER,
    }.get(edition.safe_reason or "")
    return (
        delay is not None
        and edition.workflow is EditionWorkflow.BLOCKED
        and edition.job_id is None
        and now - edition.updated_at >= delay
    )


def reopened_for_admission(edition: SubscriptionEdition, now: datetime) -> SubscriptionEdition:
    return replace(
        edition,
        workflow=EditionWorkflow.PENDING,
        updated_at=now,
        revision=edition.revision + 1,
    )
