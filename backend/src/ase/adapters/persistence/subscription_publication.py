"""Commit-free persistence adapter for the report worker's publication transaction."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.notification_enqueue import queue_edition_notifications
from ase.adapters.persistence.operational_models import ReportVersionRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.schedules import SqlScheduleRepository, project_edition_outcome
from ase.adapters.persistence.subscription_comparisons import SqlSubscriptionComparisonRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.access import AccessContext
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.schedules import Schedule, ScheduleRunResult
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import SubscriptionEdition


class SqlSubscriptionPublication:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.editions = SqlSubscriptionEditionRepository(session)

    async def baseline(self, version_id: UUID) -> tuple[ReportRecord, ReportVersion] | None:
        row = await self.session.get(ReportVersionRow, version_id, populate_existing=True)
        if row is None:
            return None
        reports = SqlReportRepository(self.session)
        report = await reports.get(row.report_id)
        version = await reports.get_version(row.report_id, row.number)
        return (report, version) if report is not None and version is not None else None

    async def schedule(self, subscription_id: UUID) -> Schedule | None:
        return await SqlScheduleRepository(self.session).get(subscription_id)

    async def add_comparison(self, comparison: EditionComparison) -> None:
        await SqlSubscriptionComparisonRepository(self.session).add(comparison)

    async def project_outcome(
        self, edition: SubscriptionEdition, result: ScheduleRunResult, access: AccessContext
    ) -> bool:
        projected = await project_edition_outcome(self.session, edition, result, access)
        if projected:
            await queue_edition_notifications(
                self.session, edition, edition.updated_at, "edition_available"
            )
            schedule = await self.schedule(edition.subscription_id)
            change = schedule.last_change if schedule is not None else None
            if (
                change is not None
                and change.status == "changed"
                and change.version_id == edition.version_id
            ):
                await queue_edition_notifications(
                    self.session, edition, edition.updated_at, "material_change"
                )
        return projected
