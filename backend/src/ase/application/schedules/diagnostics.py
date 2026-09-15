"""Private, aggregate subscription queue health projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SubscriptionDiagnostics:
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
