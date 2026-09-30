"""Session-scoped retry persistence. No method commits a partial state transition."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.monthly_report_usage import require_admission_room
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.schedules import SqlScheduleRepository
from ase.adapters.persistence.subscription_edition_codec import attempt_from_row
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import (
    due_retry_ids,
    finish_attempt,
    first_failure_at,
    latest_attempt,
)
from ase.adapters.persistence.subscription_retry_transitions import stop_waiting
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.ports.subscription_retry import SubscriptionRetrySession
from ase.application.report_jobs.recovery import SECTION_FAILURES
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionAttempt, EditionWorkflow, SubscriptionEdition
from ase.domain.subscription_monthly_budget import MonthlyBudgetPolicy


class SqlSubscriptionRetrySession:
    def __init__(self, session: AsyncSession, policy: MonthlyBudgetPolicy) -> None:
        self.session, self.policy = session, policy
        self.jobs = SqlReportJobRepository(session)
        self.editions = SqlSubscriptionEditionRepository(session)
        self.schedules = SqlScheduleRepository(session)

    async def lock_administration(self) -> None:
        await SqlUserRepository(self.session).lock_administration()

    async def latest_attempt(self, edition_id: UUID) -> EditionAttempt | None:
        row = await latest_attempt(self.session, edition_id)
        return attempt_from_row(row) if row is not None else None

    async def first_failure_at(self, edition_id: UUID) -> datetime | None:
        return await first_failure_at(self.session, edition_id)

    async def due_retry_ids(self, now: datetime) -> list[UUID]:
        return await due_retry_ids(self.session, now)

    async def recoverable_editions(self) -> list[UUID]:
        rows = await self.session.scalars(
            select(SubscriptionEditionRow.id)
            .join(ReportJobRow, SubscriptionEditionRow.job_id == ReportJobRow.id)
            .where(
                SubscriptionEditionRow.workflow == EditionWorkflow.RUNNING.value,
                ReportJobRow.status == "paused",
                ReportJobRow.error.in_({"interrupted_uncertain", *SECTION_FAILURES}),
            )
            .limit(20)
        )
        return list(rows)

    async def require_admission_room(
        self, owner_id: UUID, subscription_id: UUID, now: datetime
    ) -> None:
        await require_admission_room(self.session, owner_id, subscription_id, now, self.policy)

    async def finish_attempt(
        self,
        edition_id: UUID,
        job: ReportJob,
        lease_token: UUID,
        now: datetime,
        reason: str,
        next_retry_at: datetime | None = None,
    ) -> bool:
        return await finish_attempt(
            self.session, edition_id, job, lease_token, now, reason, next_retry_at
        )

    async def stop_waiting(
        self,
        edition: SubscriptionEdition,
        job: ReportJob,
        workflow: EditionWorkflow,
        reason: str,
        now: datetime,
    ) -> bool:
        return await stop_waiting(self.session, edition, job, workflow, reason, now)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


class SqlSubscriptionRetryTransactions:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], policy: MonthlyBudgetPolicy
    ) -> None:
        self.sessions, self.policy = sessions, policy

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SubscriptionRetrySession]:
        async with self.sessions() as session:
            yield SqlSubscriptionRetrySession(session, self.policy)
