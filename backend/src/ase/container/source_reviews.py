"""Session-local source review service; no live model or collection dependencies."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.source_reviews import SqlSourceReviewRepository
from ase.application.auditing import Auditor
from ase.application.reports.source_reviews import ReportSourceReviews

if TYPE_CHECKING:
    from ase.container import Container


def source_reviews(container: "Container", session: AsyncSession) -> ReportSourceReviews:
    repositories = container.repositories(session)
    return ReportSourceReviews(
        repositories.users,
        repositories.refresh_tokens,
        repositories.reports,
        SqlSourceReviewRepository(session),
        container.access_policy(session),
        container.clock,
        Auditor(repositories.audit, container.clock),
        repositories.uow,
    )
