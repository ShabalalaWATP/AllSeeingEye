"""Short, fenced admission of due subscriptions into the existing report-job queue."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleStore, _from_row
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.dto import RequestContext
from ase.application.report_jobs.controls import ReportJobCapacity
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.edition_planning import (
    DuePlan,
    admission_wait,
    plan_due_slots,
)
from ase.application.schedules.revision_snapshot import (
    revision_from_schedule,
)
from ase.application.schedules.runner import DueCursor
from ase.container.subscription_catchup import record_skipped, skip_covered_due, skip_unstarted
from ase.container.subscription_prepare import SubscriptionPreparation
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, RateLimited
from ase.domain.report_jobs import ReportJob
from ase.domain.research_brief_values import BriefValidationError
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
    from ase.container import Container
    from ase.domain.users import User

log = logging.getLogger(__name__)
SCHEDULE_DUE_LIMIT = 16
PENDING_DUE_LIMIT = 16


class SubscriptionAdmission(SubscriptionPreparation):
    """Prepare outside locks; reserve, admit and move cadence in one transaction."""

    def __init__(self, container: Container) -> None:
        self.container = container
        self._schedule_cursor: DueCursor | None = None
        self._pending_cursor: DueCursor | None = None

    async def run_now(
        self,
        schedule_id: UUID,
        request_id: UUID,
        actor: User,
        context: RequestContext,
        check_session: Callable[[AsyncSession], Awaitable[None]],
    ) -> SubscriptionEdition:
        identity = manual_edition_id(schedule_id, EditionTrigger.RUN_NOW, request_id)
        async with self.container.session_factory() as session:
            access = await self.container.access_policy(session).context(actor)
            row = await session.get(ScheduleRow, schedule_id)
            if row is None or row.archived_at is not None:
                raise NotFound("Subscription not found.")
            access.require_write(row.created_by, row.team_id)
            await check_session(session)
            existing = await SqlSubscriptionEditionRepository(session).get(identity)
            if existing is not None:
                return existing
            if not row.enabled:
                raise Conflict("Enable the subscription before running it.")
            schedule = _from_row(row)
        frozen, edition, candidate, owner = await self._prepare_manual(schedule, request_id, actor)
        async with (
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
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
                stored = await SqlSubscriptionEditionRepository(session).get(identity)
                if stored is None:
                    raise Conflict("Another edition is active for this subscription.")
                return stored
            except BaseException:
                await session.rollback()
                raise

    async def tick(self) -> int:
        now = self.container.clock.now()
        store = SqlScheduleStore(self.container.session_factory, self.container.access_policy)
        due, self._schedule_cursor = await store.due_batch(
            now, limit=SCHEDULE_DUE_LIMIT, cursor=self._schedule_cursor
        )
        async with self.container.session_factory() as session:
            pending_rows, self._pending_cursor = await SqlSubscriptionEditionRepository(
                session
            ).due_batch(now, limit=PENDING_DUE_LIMIT, cursor=self._pending_cursor)
        pending = [edition for edition, _ in pending_rows]
        count = 0
        for schedule in due:
            if await self._safe_enqueue(schedule=schedule):
                count += 1
        due_latest = {}
        for item in due:
            try:
                due_latest[item.id] = plan_due_slots(item, now).latest
            except ValueError:
                continue
        for edition in pending:
            if edition.due_at_utc != due_latest.get(
                edition.subscription_id
            ) and await self._safe_enqueue(edition_id=edition.id):
                count += 1
        return count

    async def _safe_enqueue(
        self, *, schedule: Schedule | None = None, edition_id: UUID | None = None
    ) -> bool:
        try:
            return await self.enqueue(schedule=schedule, edition_id=edition_id)
        except (BriefValidationError, Conflict, Forbidden, InvalidRequest, NotFound, RateLimited):
            log.warning("subscription_admission_blocked")
            return False
        except Exception:
            # Provider and source exception text can contain private inputs.
            log.warning("subscription_admission_failed")
            return False

    async def enqueue(
        self, *, schedule: Schedule | None = None, edition_id: UUID | None = None
    ) -> bool:
        if (schedule is None) == (edition_id is None):
            raise ValueError("Choose a due schedule or pending edition.")
        if schedule is not None and await skip_covered_due(self.container, schedule):
            return False
        prepared = await self._prepare(schedule=schedule, edition_id=edition_id)
        if prepared is None:
            return False
        frozen, edition, candidate, actor, plan, superseded = prepared
        async with (
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            try:
                return await self._admit(
                    session, frozen, edition, candidate, actor, plan, superseded
                )
            except BaseException:
                await session.rollback()
                raise

    async def _admit(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        session: AsyncSession,
        frozen: SubscriptionRevision,
        edition: SubscriptionEdition,
        candidate: ReportJob,
        actor: User,
        plan: DuePlan | None,
        superseded: UUID | None,
        *,
        requester: User | None = None,
        check_session: Callable[[AsyncSession], Awaitable[None]] | None = None,
        audit_context: RequestContext | None = None,
    ) -> bool:
        ledger = SqlSubscriptionEditionRepository(session)
        policy = self.container.access_policy(session)
        if requester is not None:
            requester_access = await policy.context(requester, for_update=True)
            requester_access.require_write(frozen.owner_id, frozen.team_id)
        access = await policy.background(frozen.owner_id, frozen.team_id, for_update=True)
        current_actor = access.actor
        if current_actor.id != actor.id:
            return False
        row = await session.get(ScheduleRow, edition.subscription_id, populate_existing=True)
        if (
            row is None
            or not row.enabled
            or row.archived_at is not None
            or (row.created_by, row.team_id) != (frozen.owner_id, frozen.team_id)
        ):
            return False
        if edition.due_at_utc is not None and edition.due_at_utc > self.container.clock.now():
            return False
        current_schedule = _from_row(row)
        brief = await load_schedule_brief(session, access, current_schedule)
        if brief is not None:
            standing_request_from_brief(brief, now=self.container.clock.now())
        if (
            (brief.identity.id, brief.identity.revision) if brief is not None else (None, None)
        ) != (candidate.brief_id, candidate.brief_revision):
            return False
        if edition.revision == 1 and edition.job_id is None:
            stored = await ledger.get(edition.id)
            if stored is None:
                current = _from_row(row)
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
                        or not await skip_unstarted(
                            ledger, active, edition.id, self.container.clock.now()
                        )
                    )
                ):
                    return False
                if plan is not None:
                    await record_skipped(ledger, edition, plan, frozen, self.container.clock.now())
                stored = await ledger.reserve(edition)
            elif stored.workflow is not EditionWorkflow.PENDING:
                return False
            edition = stored
        if edition.workflow is not EditionWorkflow.PENDING or edition.job_id is not None:
            return False
        if requester is not None and audit_context is not None:
            await self.container._auditor(self.container.repositories(session)).record(
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
            latest_row = await session.get(
                ScheduleRow, edition.subscription_id, populate_existing=True
            )
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
            current_brief = await load_schedule_brief(
                session, guarded_access, _from_row(latest_row)
            )
            if current_brief is not None:
                standing_request_from_brief(current_brief, now=self.container.clock.now())
            if check_session is not None:
                await check_session(session)

        try:
            job = await self.container.report_jobs(session).admit_prepared(
                current_actor,
                candidate,
                check_session=check_current,
                subscription_id=edition.subscription_id,
            )
        except MonthlyBudgetExhausted as error:
            await check_current()
            blocked = admission_wait(edition, self.container.clock.now(), budget_exhausted=True)
            if await ledger.advance(blocked, expected_revision=edition.revision) is None:
                raise Conflict() from error
            await session.commit()
            return False
        except (RateLimited, ReportJobCapacity) as error:
            await check_current()
            waiting = admission_wait(edition, self.container.clock.now(), budget_exhausted=False)
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
            updated_at=self.container.clock.now(),
            revision=edition.revision + 1,
        )
        if await ledger.advance(queued, expected_revision=edition.revision) is None:
            raise Conflict()
        if requester is not None:
            await check_current()
        if (
            edition.due_at_utc is not None
            and row.next_run_at <= edition.due_at_utc
            and (
                revision_from_schedule(
                    _from_row(row), frozen.revision, brief=brief
                ).request_snapshot
                == frozen.request_snapshot
            )
        ):
            row.next_run_at = (
                _from_row(row).recurrence.preview(self.container.clock.now(), 1)[0].utc
            )
        await session.commit()
        return True
