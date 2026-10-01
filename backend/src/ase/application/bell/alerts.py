"""Bell alerts: the scoped section, where each alert opens, and acknowledging those shown."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.bell.scope import (
    BellSignals,
    bell_visibility,
    can_acknowledge,
    in_bell_scope,
)
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.annotation_monitors import AnnotationMonitorRepository
from ase.application.ports.bell import BellAlertQueries
from ase.application.ports.reports import ReportRepository
from ase.application.ports.warning import AlertRepository
from ase.application.warning.alerts import AcknowledgeAlertUseCase
from ase.domain.bell import (
    BELL_ALERT_WINDOW,
    BELL_SHOWN,
    MAX_ACKNOWLEDGE_BATCH,
    AcknowledgeFailure,
    AcknowledgeOutcome,
    AlertDestination,
    BellAlert,
    BellAlertSection,
    BellKind,
    BellPreferences,
    DestinationKind,
)
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.users import User
from ase.domain.warning import Alert

ALERT_NOT_FOUND = "Alert not found."
REPORT_GONE = "The report made for this alert is no longer available to your account."
TRANSITION_GONE = "The annotation change behind this alert is no longer available to your account."


class BellAlerts:
    def __init__(
        self,
        queries: BellAlertQueries,
        alerts: AlertRepository,
        reports: ReportRepository,
        monitors: AnnotationMonitorRepository,
        access: AccessPolicy,
        clock: Clock,
    ) -> None:
        self._queries = queries
        self._alerts = alerts
        self._reports = reports
        self._monitors = monitors
        self._access = access
        self._clock = clock

    async def section(
        self, access: AccessContext, preferences: BellPreferences, muted_rules: frozenset[UUID]
    ) -> BellAlertSection:
        if not preferences.shows(BellKind.ALERTS):
            return BellAlertSection((), 0, muted=True)
        since = self._clock.now() - BELL_ALERT_WINDOW
        alerts, total = await self._queries.unacknowledged(
            bell_visibility(access), since, muted_rules, BELL_SHOWN
        )
        items = tuple(
            BellAlert(
                alert,
                can_acknowledge(access, alert.team_id),
                access.teams[alert.team_id].name if alert.team_id in access.teams else None,
            )
            for alert in alerts
        )
        return BellAlertSection(items, total, muted=False)

    async def _readable(self, actor: User, alert_id: UUID) -> tuple[AccessContext, Alert]:
        access = await self._access.context(actor)
        alert = await self._alerts.get(alert_id)
        if alert is None or not in_bell_scope(access, alert.created_by, alert.team_id):
            raise NotFound(ALERT_NOT_FOUND)
        return access, alert

    async def destination(self, actor: User, alert_id: UUID) -> AlertDestination:
        """Re-check the alert and its destination against the caller's current access."""
        access, alert = await self._readable(actor, alert_id)
        if alert.annotation_monitor_id is not None and alert.annotation_transition_id is not None:
            monitor = await self._monitors.get(alert.annotation_monitor_id)
            if monitor is not None and _reads(access, monitor.created_by, monitor.team_id):
                found = await self._monitors.transition(monitor.id, alert.annotation_transition_id)
                if found is not None:
                    return AlertDestination(
                        DestinationKind.TRANSITION,
                        monitor_id=monitor.id,
                        transition_id=alert.annotation_transition_id,
                    )
            return AlertDestination(
                DestinationKind.TRANSITION, available=False, message=TRANSITION_GONE
            )
        if alert.report_id is not None:
            report = await self._reports.get(alert.report_id)
            if report is not None and _reads(access, report.created_by, report.team_id):
                return AlertDestination(DestinationKind.REPORT, report_id=report.id)
            return AlertDestination(DestinationKind.REPORT, available=False, message=REPORT_GONE)
        return AlertDestination(DestinationKind.ALERTS)


def _reads(access: AccessContext, created_by: UUID | None, team_id: UUID | None) -> bool:
    try:
        access.require_read(created_by, team_id)
    except NotFound:
        return False
    return True


class BellAcknowledgements:
    """Acknowledge only the alert identifiers the bell showed, one authorised write each."""

    def __init__(
        self,
        alerts: AlertRepository,
        acknowledge: AcknowledgeAlertUseCase,
        access: AccessPolicy,
        uow: UnitOfWork,
        signals: BellSignals,
    ) -> None:
        self._alerts = alerts
        self._acknowledge = acknowledge
        self._access = access
        self._uow = uow
        self._signals = signals

    async def acknowledge(
        self, actor: User, alert_ids: Sequence[UUID], context: RequestContext
    ) -> AcknowledgeOutcome:
        unique = tuple(dict.fromkeys(alert_ids))
        if not 1 <= len(unique) <= MAX_ACKNOWLEDGE_BATCH:
            raise InvalidRequest(f"Acknowledge 1 to {MAX_ACKNOWLEDGE_BATCH} alerts at a time.")
        done: list[UUID] = []
        failed: list[AcknowledgeFailure] = []
        scopes: set[tuple[UUID | None, UUID | None]] = set()
        for alert_id in unique:
            try:
                access = await self._access.context(actor)
                alert = await self._alerts.get(alert_id)
                if alert is None or not in_bell_scope(access, alert.created_by, alert.team_id):
                    raise NotFound(ALERT_NOT_FOUND)
                # The shared use case re-checks under the administration guard, audits once
                # and returns an already acknowledged alert unchanged.
                acknowledged = await self._acknowledge.execute(actor, alert_id, context)
            except (NotFound, Forbidden, Conflict) as exc:
                await self._uow.rollback()
                failed.append(AcknowledgeFailure(alert_id, exc.message))
                continue
            done.append(acknowledged.id)
            scopes.add((acknowledged.created_by, acknowledged.team_id))
        # An already acknowledged alert returns without a write; release its guard.
        await self._uow.rollback()
        for created_by, team_id in scopes:
            await self._signals.scope(created_by, team_id)
        return AcknowledgeOutcome(tuple(done), tuple(failed))
