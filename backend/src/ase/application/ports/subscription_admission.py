"""Transaction and queue selection boundaries for subscription admission.

Each transaction owns the repositories and checks that must share one database
session. The application owns lock order and commits; adapters own session and
row handling. Preparation uses the same interface without an admission lock.
"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.ports.session import SessionCheck
from ase.application.ports.subscription_editions import SubscriptionEditionRepository
from ase.application.reports.request import ReportRequest
from ase.application.schedules.runner import DueCursor
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportVersion
from ase.domain.research_brief import ResearchBrief
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import SubscriptionEdition
from ase.domain.users import User


class SubscriptionJobAdmission(Protocol):
    async def prepare_candidate(
        self, actor: User, request_id: UUID, request: ReportRequest
    ) -> ReportJob: ...

    async def admit_prepared(
        self,
        actor: User,
        candidate: ReportJob,
        *,
        check_session: SessionCheck,
        subscription_id: UUID | None = None,
    ) -> ReportJob: ...


class SubscriptionTransaction(Protocol):
    @property
    def ledger(self) -> SubscriptionEditionRepository: ...

    @property
    def access(self) -> AccessPolicy: ...

    @property
    def jobs(self) -> SubscriptionJobAdmission: ...

    @property
    def auditor(self) -> Auditor: ...

    async def schedule(self, identity: UUID, *, refresh: bool = False) -> Schedule | None: ...
    async def advance_schedule(self, identity: UUID, next_run_at: datetime) -> None: ...
    async def brief(self, access: AccessContext, schedule: Schedule) -> ResearchBrief | None: ...
    async def report_version(self, identity: UUID, version: int) -> ReportVersion | None: ...
    async def research_available(self, owner_id: UUID, now: datetime) -> bool: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


TransactionSessionCheck = Callable[[SubscriptionTransaction], Awaitable[None]]
SourceGuard = Callable[[], AbstractAsyncContextManager[None]]


class SubscriptionTransactions(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[SubscriptionTransaction]: ...


class SubscriptionDueQueue(Protocol):
    async def schedules(
        self, now: datetime, *, limit: int, cursor: DueCursor | None
    ) -> tuple[list[Schedule], DueCursor | None]: ...

    async def editions(
        self, now: datetime, *, limit: int, cursor: DueCursor | None
    ) -> tuple[list[SubscriptionEdition], DueCursor | None]: ...
