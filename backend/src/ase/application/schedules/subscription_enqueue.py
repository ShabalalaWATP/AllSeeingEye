"""Short, fenced admission of due subscriptions into the existing report-job queue."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from ase.application.dto import RequestContext
from ase.application.ports.services import Clock
from ase.application.ports.subscription_admission import (
    SessionCheck,
    SourceGuard,
    SubscriptionDueQueue,
    SubscriptionTransaction,
    SubscriptionTransactions,
)
from ase.application.report_jobs.controls import ReportJobCapacity
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.edition_planning import (
    DuePlan,
    admission_wait,
)
from ase.application.schedules.revision_snapshot import (
    revision_from_schedule,
)
from ase.application.schedules.runner import DueCursor
from ase.application.schedules.subscription_admission_recovery import (
    rebase_overdue,
    reopen_budget_block,
)
from ase.application.schedules.subscription_catchup import (
    record_skipped,
    skip_covered_due,
    skip_unstarted,
)
from ase.application.schedules.subscription_due_tick import SubscriptionDueTick
from ase.application.schedules.subscription_prepare import SubscriptionPreparation
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, NotFound, RateLimited
from ase.domain.report_jobs import ReportJob
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import (
    EditionTrigger,
    EditionWorkflow,
    SubscriptionEdition,
    SubscriptionRevision,
    manual_edition_id,
)
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted

if TYPE_CHECKING:
    from ase.domain.users import User


class SubscriptionAdmission(SubscriptionDueTick, SubscriptionPreparation):
    """Prepare outside locks; reserve, admit and move cadence in one transaction."""

    def __init__(
        self,
        transactions: SubscriptionTransactions,
        due: SubscriptionDueQueue,
        clock: Clock,
        guard: SourceGuard,
    ) -> None:
        self.transactions, self.due = transactions, due
        self.clock, self.guard = clock, guard
        self._schedule_cursor: DueCursor | None = None
        self._pending_cursor: DueCursor | None = None

    async def run_now(
        self,
        schedule_id: UUID,
        request_id: UUID,
        actor: User,
        context: RequestContext,
        check_session: SessionCheck,
    ) -> SubscriptionEdition:
        identity = manual_edition_id(schedule_id, EditionTrigger.RUN_NOW, request_id)
        async with self.transactions() as session:
            access = await session.access.context(actor)
            row = await session.schedule(schedule_id)
            if row is None or row.archived_at is not None:
                raise NotFound("Subscription not found.")
            access.require_write(row.created_by, row.team_id)
            await check_session(session)
            existing = await session.ledger.get(identity)
            if existing is not None and (
                existing.workflow is not EditionWorkflow.PENDING
                or existing.job_id is not None
                or not row.enabled
            ):
                return existing
            if not row.enabled:
                raise Conflict("Enable the subscription before running it.")
            schedule = row
        if existing is not None:
            # A repeated request retries a job-less edition left waiting for capacity.
            await self.enqueue(edition_id=identity, requester=actor, check_session=check_session)
            async with self.transactions() as session:
                retried = await session.ledger.get(identity)
            return retried or existing
        frozen, edition, candidate, owner = await self._prepare_manual(schedule, request_id, actor)
        async with (
            self.guard(),
            self.transactions() as session,
        ):
            try:
                await self._admit(
                    session,
                    frozen,
                    edition,
                    candidate,
                    owner,
                    None,
                    None,
                    requester=actor,
                    check_session=check_session,
                    audit_context=context,
                )
                stored = await session.ledger.get(identity)
                if stored is None:
                    raise Conflict("Another edition is active for this subscription.")
                return stored
            except BaseException:
                await session.rollback()
                raise

    async def enqueue(
        self,
        *,
        schedule: Schedule | None = None,
        edition_id: UUID | None = None,
        requester: User | None = None,
        check_session: SessionCheck | None = None,
    ) -> bool:
        if (schedule is None) == (edition_id is None):
            raise ValueError("Choose a due schedule or pending edition.")
        if schedule is not None:
            schedule = await rebase_overdue(self.transactions, self.clock, self.guard, schedule)
            if schedule is None:
                return False
        await reopen_budget_block(
            self.transactions,
            self.clock,
            self.guard,
            schedule_id=schedule.id if schedule is not None else None,
            edition_id=edition_id,
        )
        if schedule is not None and await skip_covered_due(
            self.transactions, self.clock, self.guard, schedule
        ):
            return False
        prepared = await self._prepare(schedule=schedule, edition_id=edition_id)
        if prepared is None:
            return False
        frozen, edition, candidate, actor, plan, superseded = prepared
        async with (
            self.guard(),
            self.transactions() as session,
        ):
            try:
                return await self._admit(
                    session,
                    frozen,
                    edition,
                    candidate,
                    actor,
                    plan,
                    superseded,
                    requester=requester,
                    check_session=check_session,
                )
            except BaseException:
                await session.rollback()
                raise

    async def _admit(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        session: SubscriptionTransaction,
        frozen: SubscriptionRevision,
        edition: SubscriptionEdition,
        candidate: ReportJob,
        actor: User,
        plan: DuePlan | None,
        superseded: UUID | None,
        *,
        requester: User | None = None,
        check_session: SessionCheck | None = None,
        audit_context: RequestContext | None = None,
    ) -> bool:
        ledger = session.ledger
        policy = session.access
        if requester is not None:
            requester_access = await policy.context(requester, for_update=True)
            requester_access.require_write(frozen.owner_id, frozen.team_id)
        access = await policy.background(frozen.owner_id, frozen.team_id, for_update=True)
        current_actor = access.actor
        if current_actor.id != actor.id:
            return False
        row = await session.schedule(edition.subscription_id, refresh=True)
        if (
            row is None
            or not row.enabled
            or row.archived_at is not None
            or (row.created_by, row.team_id) != (frozen.owner_id, frozen.team_id)
        ):
            return False
        if edition.due_at_utc is not None and edition.due_at_utc > self.clock.now():
            return False
        current_schedule = row
        brief = await session.brief(access, current_schedule)
        if brief is not None:
            standing_request_from_brief(brief, now=self.clock.now())
        if (
            (brief.identity.id, brief.identity.revision) if brief is not None else (None, None)
        ) != (candidate.brief_id, candidate.brief_revision):
            return False
        if edition.revision == 1 and edition.job_id is None:
            stored = await ledger.get(edition.id)
            if stored is None:
                current = row
                if edition.due_at_utc is not None and (
                    plan is None or current.next_run_at != plan.due_slots[0]
                ):
                    return False
                proposed = revision_from_schedule(current, frozen.revision, brief=brief)
                if proposed.request_snapshot != frozen.request_snapshot:
                    return False
                latest = await ledger.latest_revision(current.id)
                if latest is None or latest.revision < frozen.revision:
                    await ledger.add_revision(frozen)
                elif latest != frozen:
                    return False
                active = await ledger.active(current.id)
                if (
                    active is not None
                    and active.id != edition.id
                    and (
                        active.id != superseded
                        or not await skip_unstarted(ledger, active, edition.id, self.clock.now())
                    )
                ):
                    return False
                if plan is not None:
                    await record_skipped(ledger, edition, plan, frozen, self.clock.now())
                stored = await ledger.reserve(edition)
            elif stored.workflow is not EditionWorkflow.PENDING:
                return False
            edition = stored
        if edition.workflow is not EditionWorkflow.PENDING or edition.job_id is not None:
            return False
        if requester is not None and audit_context is not None:
            await session.auditor.record(
                AuditAction.SCHEDULE_UPDATED,
                actor=requester.id,
                subject=str(edition.subscription_id),
                ip=audit_context.ip,
                details={"action": "run_now", "edition_id": str(edition.id)},
            )

        async def check_current() -> None:
            if requester is not None:
                live_requester = await policy.context(requester, for_update=True)
                live_requester.require_write(frozen.owner_id, frozen.team_id)
            guarded_access = await policy.background(
                frozen.owner_id, frozen.team_id, for_update=True
            )
            latest_row = await session.schedule(edition.subscription_id, refresh=True)
            if (
                latest_row is None
                or not latest_row.enabled
                or latest_row.archived_at is not None
                or (latest_row.created_by, latest_row.team_id) != (frozen.owner_id, frozen.team_id)
            ):
                raise Conflict("The subscription is no longer active.")
            if (
                await ledger.get_revision(edition.subscription_id, edition.frozen_revision)
                != frozen
            ):
                raise Conflict("The frozen subscription revision changed.")
            current_brief = await session.brief(guarded_access, latest_row)
            if current_brief is not None:
                standing_request_from_brief(current_brief, now=self.clock.now())
            if check_session is not None:
                await check_session(session)

        try:
            job = await session.jobs.admit_prepared(
                current_actor,
                candidate,
                check_session=check_current,
                subscription_id=edition.subscription_id,
            )
        except MonthlyBudgetExhausted as error:
            await check_current()
            blocked = admission_wait(edition, self.clock.now(), budget_exhausted=True)
            if await ledger.advance(blocked, expected_revision=edition.revision) is None:
                raise Conflict() from error
            await session.commit()
            return False
        except (RateLimited, ReportJobCapacity) as error:
            await check_current()
            waiting = admission_wait(edition, self.clock.now(), budget_exhausted=False)
            if await ledger.advance(waiting, expected_revision=edition.revision) is None:
                raise Conflict() from error
            await session.commit()
            return False
        if job.status not in ("queued", "running"):
            raise Conflict("The retained job is no longer eligible for admission.")
        queued = replace(
            edition,
            workflow=EditionWorkflow.QUEUED,
            job_id=job.id,
            safe_reason=None,
            updated_at=self.clock.now(),
            revision=edition.revision + 1,
        )
        if await ledger.advance(queued, expected_revision=edition.revision) is None:
            raise Conflict()
        if requester is not None:
            await check_current()
        # Re-read the transaction snapshot after admission/session rechecks.
        # A refreshed ORM row used to update this value implicitly.
        refreshed = await session.schedule(edition.subscription_id)
        if (
            refreshed is not None
            and edition.due_at_utc is not None
            and refreshed.next_run_at <= edition.due_at_utc
            and (
                revision_from_schedule(refreshed, frozen.revision, brief=brief).request_snapshot
                == frozen.request_snapshot
            )
        ):
            await session.advance_schedule(
                refreshed.id, refreshed.recurrence.preview(self.clock.now(), 1)[0].utc
            )
        await session.commit()
        return True
