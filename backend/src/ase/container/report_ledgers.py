"""Session-local report-ledger service with existing access and audit boundaries."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_ledgers import SqlReportLedgerRepository
from ase.application.auditing import Auditor
from ase.application.reports.report_ledgers import ReportLedgers

if TYPE_CHECKING:
    from ase.container import Container


def report_ledgers(container: "Container", session: AsyncSession) -> ReportLedgers:
    repositories = container.repositories(session)
    return ReportLedgers(
        repositories.users,
        repositories.refresh_tokens,
        repositories.reports,
        repositories.claims,
        SqlReportLedgerRepository(session),
        container.access_policy(session),
        container.clock,
        Auditor(repositories.audit, container.clock),
        repositories.uow,
    )
