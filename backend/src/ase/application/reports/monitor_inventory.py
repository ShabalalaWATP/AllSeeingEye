"""Inventory admission and exact ordered creation validation under the shared guard."""

from dataclasses import replace
from typing import TYPE_CHECKING

from ase.application.access import AccessContext
from ase.application.reports.monitor_comparisons import resolve_side
from ase.domain.annotation_monitoring import (
    AnnotationMonitor,
    InventoryCapacityUnavailable,
    InventoryHistoryGap,
    RevisionObservation,
    WatchedRevision,
)
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.errors import Conflict
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision

if TYPE_CHECKING:
    from ase.application.reports.annotation_monitors import AnnotationMonitors


def root_keys(watches: tuple[WatchedRevision, ...]) -> set[tuple[str, object]]:
    return {(w.kind, w.root_id) for w in watches}


async def complete_inventory(service: "AnnotationMonitors", monitor: AnnotationMonitor) -> None:
    if monitor.mode != "report_inventory":
        return
    actual = await service.repository.inventory(monitor)
    overflow, pending = await service.repository.pending_inventory(monitor)
    if overflow or len(actual) > 20:
        raise InventoryCapacityUnavailable(
            "The report inventory observation capacity is unavailable."
        )
    enrolled, queued = root_keys(monitor.watches), root_keys(pending)
    if len(queued) != len(pending) or enrolled & queued or root_keys(actual) != enrolled | queued:
        raise InventoryHistoryGap(
            "The complete report inventory has an unrecorded creation or missing root."
        )


async def next_watches(
    service: "AnnotationMonitors",
    access: AccessContext,
    monitor: AnnotationMonitor,
    event: RevisionObservation,
) -> tuple[WatchedRevision, ...]:
    matches = [w for w in monitor.watches if w.kind == event.kind and w.root_id == event.root_id]
    if event.previous_revision_id is None:
        if monitor.mode != "report_inventory" or matches or len(monitor.watches) >= 20:
            raise Conflict("The creation does not extend this inventory checkpoint.")
        watch = WatchedRevision(event.kind, event.root_id, event.revision_id)
        side, _ = await resolve_side(service.selector, access, replace(monitor, watches=(watch,)))
        rows: tuple[ClaimRevision | IdentityDecisionRevision | RelationshipReviewRevision, ...] = (
            *side.revisions,
            *side.identity_revisions,
            *side.relationship_revisions,
        )
        if len(rows) != 1 or rows[0].number != 1 or rows[0].previous_id is not None:
            raise Conflict("An inventory creation must identify exact revision one.")
        return tuple(sorted((*monitor.watches, watch), key=lambda w: (w.kind, str(w.root_id))))
    if len(matches) != 1 or matches[0].revision_id != event.previous_revision_id:
        raise Conflict("The next observed revision does not follow the exact checkpoint.")
    return tuple(
        replace(w, revision_id=event.revision_id) if w == matches[0] else w for w in monitor.watches
    )
