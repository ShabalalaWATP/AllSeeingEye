"""Wire publication policy to the report worker's existing transaction."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_publication import SqlSubscriptionPublication
from ase.application.access import AccessContext
from ase.application.schedules.subscription_publication import (
    publish_subscription_edition as publish,
)
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportVersion


async def publish_subscription_edition(
    session: AsyncSession,
    stored: ReportJob,
    version: ReportVersion,
    access: AccessContext,
    now: datetime,
    *,
    research_required: bool,
) -> None:
    await publish(
        SqlSubscriptionPublication(session),
        stored,
        version,
        access,
        now,
        research_required=research_required,
    )
