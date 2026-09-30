"""Wire retry policy to the worker's existing sessions and source admission guard."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_retry import (
    SqlSubscriptionRetrySession,
    SqlSubscriptionRetryTransactions,
)
from ase.application.schedules.subscription_retry import SubscriptionRetry
from ase.domain.report_jobs import ReportJob

if TYPE_CHECKING:
    from ase.container import Container


class SubscriptionRetryOrchestrator:
    def __init__(self, container: Container) -> None:
        self.container = container
        self.service = SubscriptionRetry(
            SqlSubscriptionRetryTransactions(
                container.session_factory, container.monthly_budget_policy
            ),
            container.clock,
            container.source_admission.guard,
        )

    async def pause(self, stored: ReportJob, code: str, error: BaseException | None = None) -> None:
        await self.service.pause(stored, code, error)

    async def finish_published_attempt(self, stored: ReportJob) -> None:
        await self.service.finish_published_attempt(stored)

    async def recover_expired_editions(self, session: AsyncSession, now: datetime) -> None:
        await self.service.recover_expired_editions(
            SqlSubscriptionRetrySession(session, self.container.monthly_budget_policy), now
        )

    async def resume_due(self) -> None:
        await self.service.resume_due()
