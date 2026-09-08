"""One queued correction becomes one atomic, replay-safe checkpoint transition."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from ase.application.access import AccessContext

if TYPE_CHECKING:
    from ase.application.reports.annotation_monitors import AnnotationMonitors
from ase.application.reports.comparison_manifest import comparison_json
from ase.application.reports.monitor_comparisons import (
    build_observation,
    meaningful_categories,
    resolve_side,
)
from ase.application.reports.monitor_inventory import complete_inventory, next_watches
from ase.domain.annotation_comparison import AnnotationComparison
from ase.domain.annotation_monitoring import (
    MAX_TRANSITIONS,
    AnnotationMonitor,
    AnnotationTransition,
    InventoryCapacityUnavailable,
    InventoryHistoryGap,
)
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.warning import Alert


async def _capacity(service: AnnotationMonitors, previous: AnnotationMonitor) -> None:
    if previous.checkpoint_number >= MAX_TRANSITIONS:
        raise InvalidRequest("The monitor retained transition limit is reached.")
    await service.budget(previous, 1)


async def _advance(
    service: AnnotationMonitors,
    previous: AnnotationMonitor,
    value: AnnotationMonitor,
    comparison: AnnotationComparison,
    event_id: int | None,
    *,
    reset: bool = False,
) -> AnnotationMonitor:
    await _capacity(service, previous)
    payload = comparison_json(comparison)
    old_bytes = len(await service.repository.checkpoint(previous.id))
    await service.budget(previous, 2 * len(payload) - old_bytes)
    changed = meaningful_categories(comparison)
    transition_id, checkpoint_id = uuid4(), uuid4()
    notify = not reset and value.notify_on_change and bool(set(changed) & set(value.categories))
    alert_id = uuid4() if notify else None
    value = replace(
        value, checkpoint_id=checkpoint_id, checkpoint_number=previous.checkpoint_number + 1
    )
    transition = AnnotationTransition(
        transition_id,
        value.id,
        previous.checkpoint_id,
        checkpoint_id,
        value.checkpoint_number,
        "rebaseline" if reset else "revision",
        service.clock.now(),
        changed,
        alert_id,
        comparison.comparison_sha256,
        value.revision,
        value.categories,
        value.notify_on_change,
    )
    alert = (
        None
        if alert_id is None
        else Alert(
            id=alert_id,
            indicator_id=None,
            fired_at=transition.recorded_at,
            title="Annotation review changed",
            summary="A watched annotation has a new retained review transition.",
            count=len(changed),
            threshold=1,
            event_ids=(),
            countries=(),
            report_id=value.report_id,
            created_by=value.created_by,
            team_id=value.team_id,
            annotation_monitor_id=value.id,
            annotation_transition_id=transition.id,
        )
    )
    if not await service.repository.advance(
        value, previous.revision, transition, payload, event_id, alert, reset
    ):
        raise Conflict("The monitor checkpoint changed before observation was committed.")
    return value


async def rebaseline(
    service: AnnotationMonitors,
    access: AccessContext,
    previous: AnnotationMonitor,
    value: AnnotationMonitor,
    actor_id: UUID,
) -> AnnotationMonitor:
    retained = service.codec.decode(await service.repository.checkpoint(previous.id))
    before, _ = await resolve_side(service.selector, access, previous)
    if before != retained.after:
        raise Conflict("The last valid checkpoint inputs are no longer available.")
    target = previous
    if previous.mode == "report_inventory":
        watches = await service.repository.inventory(previous)
        if len(watches) > 20:
            raise InvalidRequest("The report version exceeds the twenty-root inventory limit.")
        target = replace(previous, watches=watches)
    after, watches = await resolve_side(service.selector, access, target, latest=True)
    await _capacity(service, previous)
    comparison = build_observation(retained.after, after, actor_id, service.clock.now())
    return await _advance(
        service, previous, replace(value, watches=watches), comparison, None, reset=True
    )


async def observe(service: AnnotationMonitors, monitor_id: object) -> bool:
    if not isinstance(monitor_id, UUID):
        raise InvalidRequest("Choose a monitor identifier.")
    try:
        await service.selector.claims.users.lock_administration()
        previous = await service.repository.get(monitor_id)
        if previous is None or previous.status == "paused":
            await service.selector.uow.commit()
            return False
        try:
            access = await service.access.background(
                previous.created_by, previous.team_id, for_update=True
            )
            retained = service.codec.decode(await service.repository.checkpoint(previous.id))
            before, _ = await resolve_side(service.selector, access, previous)
            if before != retained.after:
                raise Conflict("The retained checkpoint inputs changed.")
            await complete_inventory(service, previous)
            event = await service.repository.next_event(previous.id)
            if event is None:
                # Detect a lost/out-of-band queue before calling the observation unchanged.
                _, latest = await resolve_side(service.selector, access, previous, latest=True)
                if latest != previous.watches:
                    raise Conflict(
                        "A watched revision predecessor is missing from observation history."
                    )
                if previous.status == "unavailable":
                    await service.repository.save(
                        replace(
                            previous,
                            status="active",
                            unavailable_reason=None,
                            revision=previous.revision + 1,
                            updated_at=service.clock.now(),
                        ),
                        previous.revision,
                    )
                await service.selector.uow.commit()
                return False
            watches = await next_watches(service, access, previous, event)
            value = replace(
                previous,
                watches=watches,
                revision=previous.revision + 1,
                status="active",
                unavailable_reason=None,
                updated_at=service.clock.now(),
            )
            await _capacity(service, previous)
            after, _ = await resolve_side(service.selector, access, value)
            comparison = build_observation(
                retained.after, after, value.created_by, service.clock.now()
            )
            await _advance(service, previous, value, comparison, event.id)
            await service.selector.uow.commit()
            return True
        except (Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated, ValueError) as exc:
            # Private errors and source excerpts never enter status, logs or shared alerts.
            reason = (
                "Current authority, retained inputs or storage capacity is unavailable. "
                "The last valid checkpoint is preserved."
            )
            if isinstance(exc, InventoryCapacityUnavailable):
                reason = (
                    "Inventory capacity reached (20 roots or 2,000 pending events). "
                    "The last valid checkpoint and pending history are preserved."
                )
            elif isinstance(exc, InventoryHistoryGap):
                reason = (
                    "Inventory creation history is incomplete. The last valid checkpoint is "
                    "preserved; an explicit fresh baseline is required to skip the gap."
                )
            if previous.status != "unavailable" or previous.unavailable_reason != reason:
                await service.repository.save(
                    replace(
                        previous,
                        status="unavailable",
                        unavailable_reason=reason,
                        revision=previous.revision + 1,
                        updated_at=service.clock.now(),
                    ),
                    previous.revision,
                )
            await service.selector.uow.commit()
            return False
    except BaseException:
        await service.selector.uow.rollback()
        raise
