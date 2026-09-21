"""SQL session ownership for the subscription admission application service."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.schedules import SqlScheduleStore, _from_row
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.ports.subscription_admission import SessionCheck, SubscriptionTransaction
from ase.application.report_jobs.service import ReportJobService
from ase.application.schedules.runner import DueCursor
from ase.domain.errors import Conflict
from ase.domain.report_records import ReportVersion
from ase.domain.research_brief import ResearchBrief
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import SubscriptionEdition


class SqlSubscriptionTransaction:
    def __init__(
        self,
        session: AsyncSession,
        access: AccessPolicy,
        jobs: ReportJobService,
        auditor: Auditor,
        research_available: Callable[[UUID, datetime], Awaitable[bool]],
    ) -> None:
        self.session = session
        self.access, self.jobs, self.auditor = access, jobs, auditor
        self.ledger = SqlSubscriptionEditionRepository(session)
        self._research_available = research_available

    async def schedule(self, identity: UUID, *, refresh: bool = False) -> Schedule | None:
        row = await self.session.get(ScheduleRow, identity, populate_existing=refresh)
        return _from_row(row) if row is not None else None

    async def advance_schedule(self, identity: UUID, next_run_at: datetime) -> None:
        # Admission already owns the source/admin guard; reuse its identity map.
        row = await self.session.get(ScheduleRow, identity)
        if row is None:
            raise Conflict("The subscription is no longer available.")
        row.next_run_at = next_run_at

    async def brief(self, access: AccessContext, schedule: Schedule) -> ResearchBrief | None:
        return await load_schedule_brief(self.session, access, schedule)

    async def report_version(self, identity: UUID, version: int) -> ReportVersion | None:
        return await SqlReportRepository(self.session).get_version(identity, version)

    async def research_available(self, owner_id: UUID, now: datetime) -> bool:
        return await self._research_available(owner_id, now)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


class SqlSubscriptionTransactions:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
        jobs: Callable[[AsyncSession], ReportJobService],
        auditor: Callable[[AsyncSession], Auditor],
        research_available: Callable[[AsyncSession, UUID, datetime], Awaitable[bool]],
    ) -> None:
        self._sessions, self._access = sessions, access
        self._jobs, self._auditor = jobs, auditor
        self._research_available = research_available

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SubscriptionTransaction]:
        async with self._sessions() as session:

            async def research_available(owner_id: UUID, now: datetime) -> bool:
                return await self._research_available(session, owner_id, now)

            yield SqlSubscriptionTransaction(
                session,
                self._access(session),
                self._jobs(session),
                self._auditor(session),
                research_available,
            )


class SqlSubscriptionDueQueue:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
    ) -> None:
        self._sessions = sessions
        self._schedules = SqlScheduleStore(sessions, access)

    async def schedules(
        self, now: datetime, *, limit: int, cursor: DueCursor | None
    ) -> tuple[list[Schedule], DueCursor | None]:
        return await self._schedules.due_batch(now, limit=limit, cursor=cursor)

    async def editions(
        self, now: datetime, *, limit: int, cursor: DueCursor | None
    ) -> tuple[list[SubscriptionEdition], DueCursor | None]:
        async with self._sessions() as session:
            rows, following = await SqlSubscriptionEditionRepository(session).due_batch(
                now, limit=limit, cursor=cursor
            )
            return [edition for edition, _ in rows], following


def sql_session_check(check: Callable[[AsyncSession], Awaitable[None]]) -> SessionCheck:
    """Keep API session validation in the exact transaction that admits its job."""

    async def validate(transaction: SubscriptionTransaction) -> None:
        if not isinstance(transaction, SqlSubscriptionTransaction):
            raise TypeError("A SQL session check requires a SQL subscription transaction.")
        await check(transaction.session)

    return validate
