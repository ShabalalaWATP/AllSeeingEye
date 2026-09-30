"""Recipient-scoped review dates for opt-in digests, without creating reminders."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.ledger_models import ReportLedgerHeadRow
from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.report_ledgers import SqlReportLedgerRepository
from ase.adapters.persistence.teams import TeamRow
from ase.domain.access import Visibility
from ase.domain.forecast_decisions import ForecastLedger
from ase.domain.forecast_ledger import ForecastState


async def due_review_count(
    session: AsyncSession, visibility: Visibility, since: datetime, until: datetime
) -> tuple[int, bool]:
    """Current versions scheduled in [since, until), capped at 1,000 scoped ledgers.

    The caller supplies current active membership under its delivery access lock.
    Administrator privilege never expands a recipient's email scope.
    """
    active = tuple(
        await session.scalars(
            select(TeamRow.id).where(TeamRow.id.in_(visibility.team_ids), TeamRow.is_active)
        )
    )
    recipient = Visibility(visibility.user_id, False, active)
    query = select(ReportLedgerHeadRow.id, ReportLedgerHeadRow.report_id).where(
        ReportLedgerHeadRow.kind == "forecast",
        visibility_predicate(ReportLedgerHeadRow.owner_id, ReportLedgerHeadRow.team_id, recipient),
    )
    total = int(await session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = await session.execute(
        query.order_by(ReportLedgerHeadRow.created_at.desc(), ReportLedgerHeadRow.id).limit(1000)
    )
    repository = SqlReportLedgerRepository(session)
    count = 0
    for row in rows:
        ledger = await repository.get(row.id)
        report = await session.get(ReportRow, row.report_id)
        if ledger is None or report is None or not isinstance(ledger.history, ForecastLedger):
            continue
        if (report.created_by, report.team_id) != (ledger.anchor.owner_id, ledger.anchor.team_id):
            continue
        current = ledger.history.current_version
        decision = ledger.history.latest_decision(current.version_id)
        if since <= current.review_at < until and (
            decision is None or decision.state in (ForecastState.OPEN, ForecastState.DUE)
        ):
            count += 1
    return count, total > 1000
