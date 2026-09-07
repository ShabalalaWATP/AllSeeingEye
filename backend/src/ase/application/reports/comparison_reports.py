"""Search report titles without external providers or an embedding index."""

from ase.application.dto import AccessClaims
from ase.application.ports.comparison_reports import ComparisonReportRepository
from ase.application.reports.claims import ReportClaims
from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportRecord


class ComparisonReports:
    def __init__(self, reports: ComparisonReportRepository, claims: ReportClaims) -> None:
        self.reports, self.claims = reports, claims

    async def execute(
        self, actor: AccessClaims, query: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[ReportRecord], int]:
        if len(query) > 120 or not 1 <= limit <= 50 or not 0 <= offset <= 1_000_000:
            raise InvalidRequest("Choose a bounded report title search and page.")
        try:
            access = await self.claims._context(actor)
            result = await self.reports.page(access.visibility, query.strip(), limit, offset)
            await self.claims.uow.commit()
            return result
        except BaseException:
            await self.claims.uow.rollback()
            raise
