"""Fan out only identifiers in the same transaction as a successful revision append."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.annotation_inventory import root_inventory
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
    AnnotationTransitionRow,
    AnnotationWatchRow,
)
from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.identity_models import IdentityDecisionRow
from ase.adapters.persistence.operational_models import AlertRow, ReportVersionRow
from ase.adapters.persistence.relationship_models import RelationshipReviewRow
from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.annotation_monitoring import MAX_MONITOR_PENDING_EVENTS


async def enqueue_revision(
    session: AsyncSession,
    kind: AnnotationKind,
    root_id: UUID,
    previous_id: UUID | None,
    revision_id: UUID,
    created_at: datetime,
) -> None:
    models: dict[str, type[ClaimRow] | type[IdentityDecisionRow] | type[RelationshipReviewRow]] = {
        "claim": ClaimRow,
        "identity": IdentityDecisionRow,
        "relationship": RelationshipReviewRow,
    }
    root = cast(
        ClaimRow | IdentityDecisionRow | RelationshipReviewRow | None,
        await session.get(models[kind], root_id, populate_existing=True),
    )
    if root is None:
        raise ValueError("Observation requires its retained annotation root")
    version = await session.get(ReportVersionRow, root.report_version_id)
    if version is None or version.report_id != root.report_id:
        raise ValueError("Observation requires its exact report version")
    scope = (
        AnnotationMonitorRow.team_id == root.team_id
        if root.team_id is not None
        else and_(
            AnnotationMonitorRow.team_id.is_(None),
            AnnotationMonitorRow.created_by == root.created_by,
        )
    )
    selected_ids = select(AnnotationWatchRow.monitor_id).where(
        AnnotationWatchRow.kind == kind, AnnotationWatchRow.root_id == root_id
    )
    rows = await session.scalars(
        select(AnnotationMonitorRow)
        .where(
            AnnotationMonitorRow.report_id == root.report_id,
            AnnotationMonitorRow.version_number == version.number,
            scope,
            or_(
                AnnotationMonitorRow.mode == "report_inventory",
                and_(
                    AnnotationMonitorRow.mode == "selected_roots",
                    AnnotationMonitorRow.id.in_(selected_ids),
                ),
            ),
        )
        .execution_options(populate_existing=True)
    )
    for monitor in rows:
        if monitor.mode == "report_inventory":
            if monitor.inventory_overflow:
                continue
            actual = await root_inventory(
                session,
                monitor.created_by,
                monitor.team_id,
                monitor.report_id,
                monitor.version_number,
            )
            count = await session.scalar(
                select(func.count())
                .select_from(AnnotationOutboxRow)
                .where(AnnotationOutboxRow.monitor_id == monitor.id)
            )
            if len(actual) > 20 or int(count or 0) >= MAX_MONITOR_PENDING_EVENTS:
                await session.execute(
                    update(AnnotationMonitorRow)
                    .where(AnnotationMonitorRow.id == monitor.id)
                    .values(inventory_overflow=True)
                )
                continue
        if previous_id is None and monitor.mode == "selected_roots":
            continue
        session.add(
            AnnotationOutboxRow(
                monitor_id=monitor.id,
                kind=kind,
                root_id=root_id,
                previous_revision_id=previous_id,
                revision_id=revision_id,
                created_at=created_at,
            )
        )
    await session.flush()


async def delete_report_monitors(session: AsyncSession, report_id: UUID) -> None:
    ids = select(AnnotationMonitorRow.id).where(AnnotationMonitorRow.report_id == report_id)
    await session.execute(delete(AlertRow).where(AlertRow.annotation_monitor_id.in_(ids)))
    for model in (AnnotationOutboxRow, AnnotationTransitionRow, AnnotationWatchRow):
        await session.execute(delete(model).where(model.monitor_id.in_(ids)))
    await session.execute(
        delete(AnnotationMonitorRow).where(AnnotationMonitorRow.report_id == report_id)
    )
