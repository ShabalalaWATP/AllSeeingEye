"""Alert admission intents share the alert transaction; outcome reads use the durable job."""

from dataclasses import replace
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.warning_mapping import _alert_from_row
from ase.domain.warning import Alert, AlertReportStatus


class SqlAlertReportQueue:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def due(self, now: datetime, limit: int) -> list[UUID]:
        return list(
            await self.session.scalars(
                select(AlertRow.id)
                .where(
                    AlertRow.report_status == "pending",
                    or_(
                        AlertRow.report_next_attempt_at.is_(None),
                        AlertRow.report_next_attempt_at <= now,
                    ),
                )
                # Deferred work must yield to older unattempted admission times.
                # Ordering only by firing time lets one capped owner's backlog starve others.
                .order_by(
                    AlertRow.report_next_attempt_at.asc().nulls_first(),
                    AlertRow.fired_at,
                    AlertRow.id,
                )
                .limit(limit)
            )
        )

    async def pending(self, alert_id: UUID) -> tuple[Alert, datetime] | None:
        row = await self.session.get(AlertRow, alert_id, populate_existing=True)
        if row is None or row.report_status != "pending" or row.report_rule_revision is None:
            return None
        return _alert_from_row(row), row.report_rule_revision

    async def link(self, alert_id: UUID, job_id: UUID) -> bool:
        changed = await self.session.scalar(
            update(AlertRow)
            .where(AlertRow.id == alert_id, AlertRow.report_status == "pending")
            .values(
                report_job_id=job_id,
                report_status="queued",
                report_error=None,
                report_next_attempt_at=None,
            )
            .returning(AlertRow.id)
        )
        return changed is not None

    async def defer(self, alert_id: UUID, until: datetime, reason: str) -> None:
        await self.session.execute(
            update(AlertRow)
            .where(AlertRow.id == alert_id, AlertRow.report_status == "pending")
            .values(report_next_attempt_at=until, report_error=reason)
        )

    async def stop(self, alert_id: UUID, reason: str, *, cancelled: bool = False) -> None:
        await self.session.execute(
            update(AlertRow)
            .where(AlertRow.id == alert_id, AlertRow.report_status == "pending")
            .values(
                report_status="cancelled" if cancelled else "failed",
                report_error=reason,
                report_next_attempt_at=None,
            )
        )


async def report_outcomes(session: AsyncSession, alerts: list[Alert]) -> list[Alert]:
    """One bounded projection, never decompress every job or expose a mismatched link."""
    ids = [alert.report_job_id for alert in alerts if alert.report_job_id is not None]
    if not ids:
        return [
            replace(alert, report_status="discarded", report_error=None)
            if alert.report_status == "queued"
            else alert
            for alert in alerts
        ]
    rows = await session.execute(
        select(
            ReportJobRow.id,
            ReportJobRow.owner_id,
            ReportJobRow.team_id,
            ReportJobRow.status,
            ReportJobRow.error,
        ).where(ReportJobRow.id.in_(ids))
    )
    jobs = {row.id: row for row in rows}
    result = []
    for alert in alerts:
        output = alert
        job = jobs.get(alert.report_job_id)
        if alert.report_job_id is not None:
            if job is None or (job.owner_id, job.team_id) != (alert.created_by, alert.team_id):
                output = replace(
                    alert, report_job_id=None, report_status="discarded", report_error=None
                )
            else:
                output = replace(
                    alert, report_status=cast(AlertReportStatus, job.status), report_error=job.error
                )
        elif alert.report_status == "queued":
            output = replace(alert, report_status="discarded", report_error=None)
        result.append(output)
    return result
