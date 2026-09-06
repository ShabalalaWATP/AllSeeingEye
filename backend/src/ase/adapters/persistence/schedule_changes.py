"""Save a research comparison and optional scoped alert inside the authorised run commit."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AlertRow, ReportRow, ReportVersionRow, ScheduleRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.application.access import AccessContext
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.report_records import ReportVersion
from ase.domain.research_changes import change_from_dict, change_to_dict, compare_reports


async def _baseline(
    session: AsyncSession, schedule: ScheduleRow, access: AccessContext
) -> ReportVersion | None:
    change = change_from_dict(schedule.last_change)
    if change is None or change.baseline_version_id is None:
        return None
    version = await session.get(ReportVersionRow, change.baseline_version_id)
    if version is None:
        return None
    report = await session.get(ReportRow, version.report_id, populate_existing=True)
    if report is None:
        return None
    try:
        access.require_same_scope(
            schedule.created_by, schedule.team_id, report.created_by, report.team_id
        )
    except (Forbidden, InvalidRequest, NotFound):
        return None
    return await SqlReportRepository(session).get_version(report.id, version.number)


async def record_change(
    session: AsyncSession,
    schedule: ScheduleRow,
    report: ReportRow,
    access: AccessContext,
    ran_at: datetime,
) -> None:
    if not schedule.notify_on_change:
        return
    # A newly scheduled report begins at version one. Later manual regeneration
    # must not silently substitute a different comparison result.
    current = await SqlReportRepository(session).get_version(report.id, 1)
    if current is None:
        return
    previous = await _baseline(session, schedule, access)
    change = compare_reports(previous, current)
    schedule.last_change = change_to_dict(change)
    if change.status != "changed":
        return
    session.add(
        AlertRow(
            id=uuid4(),
            indicator_id=None,
            schedule_id=schedule.id,
            fired_at=ran_at,
            title=f"Evidence changed: {schedule.name}"[:200],
            summary=change.summary,
            count=max(1, change.added + change.removed + change.updated),
            threshold=1,
            event_ids=[item.event_id for item in current.evidence[:20]],
            countries=sorted({item.country_iso for item in current.evidence if item.country_iso})[
                :20
            ],
            report_id=report.id,
            created_by=schedule.created_by,
            team_id=schedule.team_id,
        )
    )
