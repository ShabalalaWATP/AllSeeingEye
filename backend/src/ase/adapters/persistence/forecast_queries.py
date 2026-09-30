"""Filter scope before bounded forecast indexing; deduplicate reminder receipts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.ledger_models import ForecastReminderRow, ReportLedgerHeadRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.access import Visibility
from ase.domain.forecast_views import ForecastIndex
from ase.domain.report_ledgers import ReportLedgerAnchor


async def index(
    session: AsyncSession,
    visibility: Visibility,
    team_id: UUID | None,
    personal: bool,
    limit: int,
    offset: int,
) -> tuple[tuple[ForecastIndex, ...], int]:
    query = (
        select(
            ReportLedgerHeadRow.id,
            ReportLedgerHeadRow.report_id,
            ReportVersionRow.number,
            ReportRow.title,
        )
        .join(ReportRow, ReportRow.id == ReportLedgerHeadRow.report_id)
        .join(ReportVersionRow, ReportVersionRow.id == ReportLedgerHeadRow.report_version_id)
        .where(
            ReportLedgerHeadRow.kind == "forecast",
            visibility_predicate(
                ReportLedgerHeadRow.owner_id, ReportLedgerHeadRow.team_id, visibility
            ),
        )
    )
    if team_id is not None:
        query = query.where(ReportLedgerHeadRow.team_id == team_id)
    elif personal:
        query = query.where(
            ReportLedgerHeadRow.team_id.is_(None),
            ReportLedgerHeadRow.owner_id == visibility.user_id,
        )
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = await session.execute(
        query.order_by(ReportLedgerHeadRow.created_at.desc(), ReportLedgerHeadRow.id)
        .limit(limit)
        .offset(offset)
    )
    return tuple(ForecastIndex(*row) for row in rows), total


async def reminder(
    session: AsyncSession,
    anchor: ReportLedgerAnchor,
    version_id: UUID,
    review_at: datetime,
    now: datetime,
) -> datetime:
    row = await session.get(ForecastReminderRow, (version_id, review_at))
    if row is None:
        row = ForecastReminderRow(
            version_id=version_id, review_at=review_at, ledger_id=anchor.id, reminded_at=now
        )
        session.add(row)
        await session.flush()
    return row.reminded_at
