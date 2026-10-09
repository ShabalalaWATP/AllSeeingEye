"""Edit timing and name without replacing a subscription's pinned analytical request."""

from dataclasses import dataclass, replace
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.session import SessionCheck
from ase.application.ports.subscription_settings import SubscriptionSettingsStore
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.schedules import Schedule
from ase.domain.subscription_recurrence import LocalRecurrence
from ase.domain.subscription_settings import settings_revision
from ase.domain.users import User

STALE_SETTINGS = "The subscription settings changed. Reload subscriptions before editing again."


@dataclass(frozen=True, slots=True)
class BriefSettingsInput:
    expected_revision: str
    name: str
    recurrence: LocalRecurrence


class EditBriefSettings:
    def __init__(
        self,
        store: SubscriptionSettingsStore,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.store, self.access, self.clock = store, access, clock
        self.auditor, self.uow = auditor, uow

    async def execute(
        self,
        actor: User,
        subscription_id: UUID,
        data: BriefSettingsInput,
        context: RequestContext,
        *,
        check_session: SessionCheck | None = None,
    ) -> Schedule:
        access = await self.access.context(actor, for_update=True)
        existing = await self.store.get(subscription_id)
        if existing is None or existing.archived_at is not None:
            raise NotFound("Subscription not found.")
        access.require_write(existing.created_by, existing.team_id)
        if existing.brief_id is None:
            raise InvalidRequest(
                "Use the standard editor for subscriptions without a Research Brief."
            )
        if data.expected_revision != settings_revision(existing):
            raise Conflict(STALE_SETTINGS)
        name = " ".join(data.name.split())
        if not 1 <= len(name) <= 120:
            raise InvalidRequest(
                "Enter a name of at most 120 characters.",
                fields={"name": "Enter a name of at most 120 characters."},
            )
        recurrence = data.recurrence
        updated = replace(
            existing,
            name=name,
            timezone=recurrence.timezone,
            hour_utc=recurrence.hour,
            local_hour=recurrence.hour,
            local_minute=recurrence.minute,
            cadence=recurrence.cadence,
            weekday=recurrence.weekday,
            monthday=recurrence.monthday,
            anchor_month=recurrence.anchor_month,
            next_run_at=recurrence.preview(self.clock.now(), 1)[0].utc
            if recurrence != existing.recurrence
            else existing.next_run_at,
        )
        saved = await self.store.update(existing, updated)
        if saved is None:
            raise Conflict(STALE_SETTINGS)
        await self.auditor.record(
            AuditAction.SCHEDULE_UPDATED,
            actor=actor.id,
            subject=str(saved.id),
            ip=context.ip,
            details={"name": saved.name, "action": "edit_brief_settings"},
        )
        if check_session is not None:
            await check_session()
        await self.uow.commit()
        return saved
