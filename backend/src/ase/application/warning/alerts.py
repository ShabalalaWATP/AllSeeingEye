"""Read and acknowledge alerts within their preserved personal or team scope."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import timedelta
from uuid import UUID

from ase.application.access import AccessPolicy, OwnershipScope
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.warning import AlertRepository
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.users import User
from ase.domain.warning import Alert

DEFAULT_SPAN = timedelta(days=7)
MAX_ALERTS = 200


@dataclass(frozen=True, slots=True)
class AlertListing:
    items: list[Alert]
    # Display names for the owners of personal alerts in ``items``.
    owner_names: dict[UUID, str] = field(default_factory=dict)

    def owner_name(self, alert: Alert) -> str | None:
        """Team alerts are identified by their workspace, so only personal ones carry a name."""
        if alert.team_id is not None or alert.created_by is None:
            return None
        return self.owner_names.get(alert.created_by)

    @property
    def unacknowledged(self) -> int:
        return sum(1 for item in self.items if item.acknowledged_at is None)


class ListAlertsUseCase:
    def __init__(self, alerts: AlertRepository, clock: Clock, access: AccessPolicy) -> None:
        self._alerts = alerts
        self._clock = clock
        self._access = access

    async def execute(
        self,
        actor: User,
        *,
        hours: int | None = None,
        limit: int = 50,
        scope: OwnershipScope = "mine",
    ) -> AlertListing:
        """Every role defaults to its own personal and current-team alerts (KAN-90)."""
        span = DEFAULT_SPAN if hours is None else timedelta(hours=max(1, min(hours, 24 * 30)))
        access = await self._access.context(actor)
        items = await self._alerts.list_recent(
            self._clock.now() - span,
            max(1, min(limit, MAX_ALERTS)),
            access.scoped_visibility(scope),
        )
        personal = (item.created_by for item in items if item.team_id is None)
        owners = await self._access.owner_names(actor, (o for o in personal if o is not None))
        return AlertListing(items, owners)


class AcknowledgeAlertUseCase:
    def __init__(
        self,
        alerts: AlertRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._alerts = alerts
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def execute(
        self,
        actor: User,
        alert_id: UUID,
        context: RequestContext,
        *,
        disposition: AlertDisposition | None = None,
        note: str | None = None,
    ) -> Alert:
        if note is not None and (len(note) > 200 or any(ord(char) < 32 for char in note)):
            raise InvalidRequest("Use at most 200 plain-text characters for the note.")
        access = await self._access.context(actor, for_update=True)
        alert = await self._alerts.get(alert_id)
        if alert is None:
            raise NotFound("Alert not found.")
        access.require_read(alert.created_by, alert.team_id)
        access.require_create(alert.team_id)
        if alert.acknowledged_at is not None:
            return alert
        acknowledged = replace(
            alert,
            acknowledged_at=self._clock.now(),
            acknowledged_by=actor.id,
            disposition=disposition,
            disposition_note=note,
        )
        if not await self._alerts.acknowledge(acknowledged):
            raise Conflict("This alert was acknowledged concurrently. Reload its shared decision.")
        await self._auditor.record(
            AuditAction.ALERT_ACKNOWLEDGED, actor=actor.id, subject=str(alert.id), ip=context.ip,
            details={"title": alert.title},
        )  # fmt: skip
        await self._uow.commit()
        return acknowledged
