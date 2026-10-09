"""Admit one alert's durable report outside evaluation and outside provider work."""

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from ase.application.access import AccessPolicy
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.alert_reports import AlertReportQueue
from ase.application.ports.warning import IndicatorRepository
from ase.application.report_jobs.controls import ReportJobCapacity
from ase.application.report_jobs.service import ReportJobService
from ase.application.reports.request import ReportRequest
from ase.domain.errors import (
    Conflict,
    Forbidden,
    NotFound,
    RateLimited,
    Unauthenticated,
)
from ase.domain.users import User
from ase.domain.warning import Alert, Indicator


def alert_request_key(alert_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"ase:alert-report:{alert_id}")


def alert_report_request(rule: Indicator, alert: Alert) -> ReportRequest:
    """Anchor the existing rounded window to its firing, even after capacity retries."""
    if rule.report_template is None:
        raise Forbidden()
    return ReportRequest(
        template_id=rule.report_template,
        country_iso=rule.countries[0] if len(rule.countries) == 1 else None,
        research_since=alert.fired_at - timedelta(hours=max(1, -(-rule.window_minutes // 60))),
        # The evaluator includes the firing instant; report intervals are half-open.
        research_until=alert.fired_at + timedelta(microseconds=1),
        plan_id=rule.plan_id,
        team_id=rule.team_id,
        automation=True,
    )


class AdmitAlertReport:
    def __init__(
        self,
        queue: AlertReportQueue,
        indicators: IndicatorRepository,
        jobs: ReportJobService,
        access: AccessPolicy,
        uow: UnitOfWork,
        clock: Clock,
        guard: Callable[[], AbstractAsyncContextManager[None]],
    ) -> None:
        self.queue, self.indicators, self.jobs = queue, indicators, jobs
        self.access, self.uow, self.clock, self.guard = access, uow, clock, guard

    async def _current(self, alert: Alert, rule: Indicator, *, locked: bool) -> User:
        if alert.created_by is None:
            raise Forbidden()
        access = await self.access.background(alert.created_by, alert.team_id, for_update=locked)
        current = await self.indicators.get(rule.id)
        pending = await self.queue.pending(alert.id)
        if (
            pending is None
            or current != rule
            or not rule.enabled
            or rule.updated_at != pending[1]
            or (rule.created_by, rule.team_id) != (alert.created_by, alert.team_id)
        ):
            raise Forbidden()
        return access.actor

    async def execute(self, alert_id: UUID) -> None:
        """No paid calls occur here; commit the job and its alert link atomically."""
        try:
            async with asyncio.timeout(30):
                found = await self.queue.pending(alert_id)
                if found is None:
                    return
                alert, revision = found
                if self.clock.now() - alert.fired_at > timedelta(days=1):
                    await self.queue.stop(alert_id, "admission_expired")
                    await self.uow.commit()
                    return
                rule = await self.indicators.get(alert.indicator_id) if alert.indicator_id else None
                if rule is None or rule.updated_at != revision:
                    raise Forbidden()
                owner = await self._current(alert, rule, locked=False)
                await self.uow.rollback()
                candidate = await self.jobs.prepare_candidate(
                    owner, alert_request_key(alert.id), alert_report_request(rule, alert)
                )
                candidate.payload["alert_id"] = str(alert.id)
                async with self.guard():
                    owner = await self._current(alert, rule, locked=True)

                    async def check() -> None:
                        await self._current(alert, rule, locked=True)

                    admitted = await self.jobs.admit_prepared(owner, candidate, check_session=check)
                    if not await self.queue.link(alert.id, admitted.id):
                        raise Conflict()
                    await self.uow.commit()
        except asyncio.CancelledError:
            await self.uow.rollback()
            raise  # The durable pending intent survives shutdown, without a paid replay.
        except (Forbidden, NotFound, Unauthenticated):
            await self.uow.rollback()
            await self.queue.stop(alert_id, "access_or_rule_changed", cancelled=True)
            await self.uow.commit()
        except (RateLimited, ReportJobCapacity):
            await self.uow.rollback()
            await self.queue.defer(
                alert_id, self.clock.now() + timedelta(minutes=5), "capacity_wait"
            )
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            # Fixed text only; provider/configuration exceptions can contain private inputs.
            await self.queue.stop(alert_id, "admission_failed")
            await self.uow.commit()
