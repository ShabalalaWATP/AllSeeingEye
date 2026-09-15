"""Load a deliberately selected reviewer snapshot with exact-version authority."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.dto import AccessClaims
from ase.container import Container
from ase.container.source_reviews import source_reviews
from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.source_review_records import SourceReviewSnapshot


async def selected_reviewed_snapshot(
    claims: AccessClaims,
    container: Container,
    session: AsyncSession,
    record: ReportRecord,
    version: ReportVersion,
    requested_number: int | None,
    snapshot_id: UUID | None,
) -> SourceReviewSnapshot | None:
    if snapshot_id is None:
        return None
    if requested_number is None or requested_number != version.number:
        raise InvalidRequest("Choose an exact report version with a source snapshot.")
    return await source_reviews(container, session).snapshot(
        claims, record.id, requested_number, snapshot_id
    )
