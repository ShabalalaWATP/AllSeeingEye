"""Fan out only identifiers in the same transaction as a successful revision append."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
    AnnotationTransitionRow,
    AnnotationWatchRow,
)
from ase.adapters.persistence.operational_models import AlertRow
from ase.domain.annotation_comparison import AnnotationKind


async def enqueue_revision(
    session: AsyncSession,
    kind: AnnotationKind,
    root_id: UUID,
    previous_id: UUID,
    revision_id: UUID,
    created_at: datetime,
) -> None:
    ids = await session.scalars(
        select(AnnotationWatchRow.monitor_id).where(
            AnnotationWatchRow.kind == kind, AnnotationWatchRow.root_id == root_id
        )
    )
    for monitor_id in ids:
        session.add(
            AnnotationOutboxRow(
                monitor_id=monitor_id,
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
