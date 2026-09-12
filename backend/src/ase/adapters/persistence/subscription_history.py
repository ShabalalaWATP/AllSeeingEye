"""Retain bounded content fingerprints across empty or failed subscription editions."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ReportRow, ScheduleRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.application.reports.subscription_updates import content_signature
from ase.domain.reports import ReportStatus


async def remember_evidence(
    session: AsyncSession, schedule: ScheduleRow, report: ReportRow
) -> None:
    """Caller already authorises the owner, schedule and report scope under the write guard."""
    current = await SqlReportRepository(session).get_version(report.id, 1)
    if current is None or current.status is ReportStatus.FAILED or not current.evidence:
        return
    options = dict(schedule.research_options or {})
    old = list(options.get("seen_content_signatures", ()))
    new = [content_signature(item) for item in current.evidence]
    # Latest-seen entries win; nothing here is raw event data or a cross-user cache.
    ordered = list(dict.fromkeys([*reversed(new), *reversed(old)]))[:500]
    options["seen_content_signatures"] = list(reversed(ordered))
    options["baseline_report_id"] = str(report.id)
    schedule.research_options = options
