"""Read and acknowledge alerts within their preserved personal or team scope."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.warning import AlertRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import NotFound
from ase.domain.users import User
from ase.domain.warning import Alert

DEFAULT_SPAN = timedelta(days=7)
MAX_ALERTS = 200


class ListAlertsUseCase:
    def __init__(self, alerts: AlertRepository, clock: Clock, access: AccessPolicy) -> None:
        self._alerts = alerts
        self._clock = clock
        self._access = access

    async def execute(
        self, actor: User, *, hours: int | None = None, limit: int = 50
    ) -> list[Alert]:
        span = DEFAULT_SPAN if hours is None else timedelta(hours=max(1, min(hours, 24 * 30)))
        access = await self._access.context(actor)
        return await self._alerts.list_recent(
            self._clock.now() - span, max(1, min(limit, MAX_ALERTS)), access.visibility
        )


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

    async def execute(self, actor: User, alert_id: UUID, context: RequestContext) -> Alert:
        access = await self._access.context(actor, for_update=True)
        alert = await self._alerts.get(alert_id)
        if alert is None:
            raise NotFound("Alert not found.")
        access.require_read(alert.created_by, alert.team_id)
        access.require_create(alert.team_id)
        if alert.acknowledged_at is not None:
            return alert
        acknowledged = replace(alert, acknowledged_at=self._clock.now(), acknowledged_by=actor.id)
        await self._alerts.save(acknowledged)
        await self._auditor.record(
            AuditAction.ALERT_ACKNOWLEDGED, actor=actor.id, subject=str(alert.id), ip=context.ip,
            details={"title": alert.title},
        )  # fmt: skip
        await self._uow.commit()
        return acknowledged
