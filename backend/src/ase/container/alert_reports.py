"""Wire bounded alert admission and fence its origin during durable execution/publication."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_reports import SqlAlertReportQueue
from ase.adapters.persistence.operational_models import AlertRow, IndicatorRow
from ase.application.schedules.runner import ScheduleRunner
from ase.application.warning.report_admission import AdmitAlertReport, alert_request_key
from ase.domain.errors import Forbidden
from ase.domain.report_jobs import ReportJob

if TYPE_CHECKING:
    from ase.container import Container


class AlertReportAdmission:
    """One sequential bounded page per tick, with independent per-intent failures."""

    def __init__(self, container: "Container") -> None:
        self.container = container

    async def tick(self) -> int:
        container = self.container
        async with container.session_factory() as session:
            pending = await SqlAlertReportQueue(session).due(container.clock.now(), 8)
        for alert_id in pending:
            async with container.session_factory() as session:
                repos = container.repositories(session)
                await AdmitAlertReport(
                    SqlAlertReportQueue(session),
                    repos.indicators,
                    container.report_jobs(session),
                    container.access_policy(session),
                    repos.uow,
                    container.clock,
                    container.source_admission.guard,
                ).execute(alert_id)
        return len(pending)


def alert_report_runner(container: "Container") -> ScheduleRunner:
    # The existing runner owns one start/stop task. Admission never creates per-alert tasks.
    return ScheduleRunner(
        AlertReportAdmission(container).tick, worker_name="alert_report_admission"
    )


async def require_alert_origin(session: AsyncSession, job: ReportJob) -> None:
    value = job.payload.get("alert_id")
    if value is None:
        return
    try:
        alert_id = UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise Forbidden() from None
    alert = await session.get(AlertRow, alert_id, populate_existing=True)
    rule = (
        await session.get(IndicatorRow, alert.indicator_id, populate_existing=True)
        if alert is not None and alert.indicator_id is not None
        else None
    )
    if (
        alert is None
        or rule is None
        or not rule.enabled
        or rule.updated_at != alert.report_rule_revision
        or (alert.created_by, alert.team_id) != (job.owner_id, job.team_id)
        or (rule.created_by, rule.team_id) != (job.owner_id, job.team_id)
        or job.request_key != alert_request_key(alert.id)
        or (
            alert.report_job_id != job.id
            and not (alert.report_job_id is None and alert.report_status == "pending")
        )
    ):
        raise Forbidden()


async def publish_alert_report(session: AsyncSession, job: ReportJob) -> None:
    if job.payload.get("alert_id") is None:
        return
    await require_alert_origin(session, job)
    linked = await session.scalar(
        update(AlertRow)
        .where(AlertRow.report_job_id == job.id)
        .values(report_id=job.report_id)
        .returning(AlertRow.id)
    )
    if linked is None:
        raise Forbidden()
