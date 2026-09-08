"""Read exact retained transitions under current monitor and parent authority."""

import json
from dataclasses import asdict, replace
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.reports.annotation_monitors import AnnotationMonitors
from ase.application.reports.comparison_manifest import MAX_COMPARISON_BYTES
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.application.reports.monitor_comparisons import resolve_side
from ase.domain.annotation_comparison import AnnotationComparison, ComparisonSide
from ase.domain.annotation_monitoring import AnnotationTransition, WatchedRevision
from ase.domain.errors import Conflict, InvalidRequest, NotFound, RateLimited


def _watches(side: ComparisonSide) -> tuple[WatchedRevision, ...]:
    return tuple(
        sorted(
            [WatchedRevision("claim", r.claim_id, r.id) for r in side.revisions]
            + [WatchedRevision("identity", r.decision_id, r.id) for r in side.identity_revisions]
            + [
                WatchedRevision("relationship", r.relationship_id, r.id)
                for r in side.relationship_revisions
            ],
            key=lambda w: (w.kind, str(w.root_id)),
        )
    )


async def list_transitions(
    service: AnnotationMonitors, actor: AccessClaims, key: UUID, limit: int, offset: int
) -> tuple[list[AnnotationTransition], int]:
    if not 1 <= limit <= 50 or not 0 <= offset <= 1_000_000:
        raise InvalidRequest("Choose a bounded transition history page.")
    try:
        access = await service.selector.claims._context(actor)
        monitor = await service.current(access, key)
        await resolve_side(service.selector, access, monitor)
        result = await service.repository.history(key, limit, offset)
        await service.selector.uow.commit()
        return result
    except BaseException:
        await service.selector.uow.rollback()
        raise


async def retained_transition(
    service: AnnotationMonitors,
    actor: AccessClaims,
    key: UUID,
    transition_id: UUID,
    expected_digest: str | None = None,
) -> tuple[AnnotationTransition, AnnotationComparison, bytes]:
    if not _PACKAGE_SLOTS.acquire(blocking=False):
        raise RateLimited(5)
    try:
        access = await service.selector.claims._context(actor)
        monitor = await service.current(access, key)
        record = await service.repository.transition(key, transition_id)
        if record is None:
            raise NotFound("The retained transition is unavailable or has expired.")
        metadata, payload = record
        comparison = service.codec.decode(payload)
        if metadata.comparison_sha256 != comparison.comparison_sha256 or (
            expected_digest is not None and expected_digest != metadata.comparison_sha256
        ):
            raise Conflict(
                "The selected retained transition digest differs. Reload the transition."
            )
        # These are exact historical roots, never mutable current heads. Hold one guard
        # across both input sets through the final commit, as with comparison exports.
        for snapshot in (comparison.before, comparison.after):
            if (
                snapshot.report_id != monitor.report_id
                or snapshot.version_number != monitor.version_number
            ):
                raise Conflict("The retained transition has a different report anchor.")
            historical = {(w.kind, w.root_id) for w in _watches(snapshot)}
            enrolled = {(w.kind, w.root_id) for w in monitor.watches}
            if (
                monitor.mode == "selected_roots" and historical != enrolled
            ) or not historical.issubset(enrolled):
                raise Conflict("The retained transition has a different watched selection.")
            actual, _ = await resolve_side(
                service.selector, access, replace(monitor, watches=_watches(snapshot))
            )
            if actual != snapshot:
                raise Conflict("The retained transition inputs are no longer available unchanged.")
        artifact = json.dumps(
            {"transition": asdict(metadata), "comparison": json.loads(payload)},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        if len(artifact) > MAX_COMPARISON_BYTES:
            raise InvalidRequest("The complete transition manifest exceeds its export limit.")
        await service.selector.uow.commit()
        return metadata, comparison, artifact
    except BaseException:
        await service.selector.uow.rollback()
        raise
    finally:
        _PACKAGE_SLOTS.release()
