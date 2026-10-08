"""Records outside a report that pin it, and children removed with it.

Subscription editions, their comparisons and lineages pin exact report versions without
cascading foreign keys. A completed edition must keep a saved version, and a comparison
always names its current version, so those links cannot be detached without a migration.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.adapters.persistence.models import ReportVersionRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionComparisonRow,
    SubscriptionEditionRow,
    SubscriptionLineageRow,
)


async def retained_by_subscription(session: AsyncSession, report_id: UUID) -> bool:
    """Whether any subscription edition, comparison or lineage pins this report."""
    versions = select(ReportVersionRow.id).where(ReportVersionRow.report_id == report_id)
    edition = SubscriptionEditionRow
    comparison = SubscriptionEditionComparisonRow
    lineage = SubscriptionLineageRow
    query = select(
        or_(
            exists().where(
                or_(
                    edition.report_id == report_id,
                    edition.version_id.in_(versions),
                    edition.baseline_version_id.in_(versions),
                )
            ),
            exists().where(
                or_(
                    comparison.current_version_id.in_(versions),
                    comparison.previous_version_id.in_(versions),
                )
            ),
            exists().where(lineage.analytical_baseline_version_id.in_(versions)),
        )
    )
    return bool(await session.scalar(query))


async def delete_citation_verdicts(session: AsyncSession, report_id: UUID) -> None:
    """Explicit cleanup for SQLite connections without foreign key enforcement."""
    versions = select(ReportVersionRow.id).where(ReportVersionRow.report_id == report_id)
    await session.execute(
        delete(CitationVerdictRow).where(
            or_(
                CitationVerdictRow.report_id == report_id,
                CitationVerdictRow.report_version_id.in_(versions),
            )
        )
    )
