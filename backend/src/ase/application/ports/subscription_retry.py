"""Transactional retry dependencies; the application owns decisions and lock order."""

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.ports.schedules import ScheduleRepository
from ase.application.ports.subscription_editions import SubscriptionEditionRepository
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionAttempt, EditionWorkflow, SubscriptionEdition


class SubscriptionRetrySession(Protocol):
    @property
    def jobs(self) -> ReportJobRepository: ...
    @property
    def editions(self) -> SubscriptionEditionRepository: ...
    @property
    def schedules(self) -> ScheduleRepository: ...
    async def lock_administration(self) -> None: ...
    async def latest_attempt(self, edition_id: UUID) -> EditionAttempt | None: ...
    async def first_failure_at(self, edition_id: UUID) -> datetime | None: ...
    async def due_retry_ids(self, now: datetime) -> list[UUID]: ...
    async def due_blocked_ids(self, now: datetime) -> list[UUID]: ...
    async def recoverable_editions(self) -> list[UUID]: ...
    async def require_admission_room(
        self, owner_id: UUID, subscription_id: UUID, now: datetime
    ) -> None: ...
    async def finish_attempt(
        self,
        edition_id: UUID,
        job: ReportJob,
        lease_token: UUID,
        now: datetime,
        reason: str,
        next_retry_at: datetime | None = None,
    ) -> bool: ...
    async def stop_waiting(
        self,
        edition: SubscriptionEdition,
        job: ReportJob,
        workflow: EditionWorkflow,
        reason: str,
        now: datetime,
    ) -> bool: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SubscriptionRetryTransactions(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[SubscriptionRetrySession]: ...
