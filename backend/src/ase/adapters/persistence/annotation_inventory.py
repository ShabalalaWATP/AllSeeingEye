"""Bounded same-parent, same-scope inventory and retained creation coverage."""

from typing import cast
from uuid import UUID

from sqlalchemy import and_, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
)
from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.identity_models import IdentityDecisionRow
from ase.adapters.persistence.operational_models import ReportVersionRow
from ase.adapters.persistence.relationship_models import RelationshipReviewRow
from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.annotation_monitoring import (
    MAX_MONITOR_PENDING_EVENTS,
    AnnotationMonitor,
    WatchedRevision,
)


async def inventory(
    session: AsyncSession, monitor: AnnotationMonitor
) -> tuple[WatchedRevision, ...]:
    return await root_inventory(
        session, monitor.created_by, monitor.team_id, monitor.report_id, monitor.version_number
    )


async def root_inventory(
    session: AsyncSession, owner: UUID, team: UUID | None, report: UUID, number: int
) -> tuple[WatchedRevision, ...]:
    queries = []
    for kind, model in (
        ("claim", ClaimRow),
        ("identity", IdentityDecisionRow),
        ("relationship", RelationshipReviewRow),
    ):
        scope = (
            model.team_id == team
            if team is not None
            else and_(model.team_id.is_(None), model.created_by == owner)
        )
        queries.append(
            select(
                literal(kind).label("kind"),
                model.id.label("root_id"),
                model.latest_revision_id.label("revision_id"),
            )
            .join(ReportVersionRow, ReportVersionRow.id == model.report_version_id)
            .where(
                model.report_id == report,
                ReportVersionRow.report_id == report,
                ReportVersionRow.number == number,
                scope,
            )
        )
    rows = await session.execute(union_all(*queries).order_by("kind", "root_id").limit(21))
    return tuple(
        WatchedRevision(cast(AnnotationKind, r.kind), r.root_id, r.revision_id) for r in rows
    )


async def pending_inventory(
    session: AsyncSession, monitor: AnnotationMonitor
) -> tuple[bool, tuple[WatchedRevision, ...]]:
    overflow = await session.scalar(
        select(AnnotationMonitorRow.inventory_overflow).where(AnnotationMonitorRow.id == monitor.id)
    )
    rows = list(
        await session.scalars(
            select(AnnotationOutboxRow)
            .where(AnnotationOutboxRow.monitor_id == monitor.id)
            .order_by(AnnotationOutboxRow.id)
            .limit(MAX_MONITOR_PENDING_EVENTS + 1)
        )
    )
    creations = tuple(
        WatchedRevision(cast(AnnotationKind, r.kind), r.root_id, r.revision_id)
        for r in rows
        if r.previous_revision_id is None
    )
    return bool(overflow) or len(rows) > MAX_MONITOR_PENDING_EVENTS, creations
