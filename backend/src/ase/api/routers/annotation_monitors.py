"""Private opt-in annotation monitors and exact retained transition downloads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep, get_current_user
from ase.api.schemas_annotation_monitors import (
    AnnotationMonitorCreateIn,
    AnnotationMonitorOut,
    AnnotationMonitorsOut,
    AnnotationMonitorUpdateIn,
    AnnotationTransitionDetailOut,
    AnnotationTransitionExportIn,
    AnnotationTransitionOut,
    AnnotationTransitionsOut,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.reports.monitor_history import list_transitions, retained_transition

router = APIRouter(
    prefix="/annotation-monitors",
    tags=["annotation-monitors"],
    dependencies=[Depends(get_current_user)],
)


@router.post("")
async def create_monitor(
    body: AnnotationMonitorCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> AnnotationMonitorOut:
    await validate_request_session(container, claims)
    result = await container.annotation_monitors(session).create(
        claims, body.name, body.selection.to_domain(), tuple(body.categories), body.notify_on_change
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationMonitorOut.from_monitor(result)


@router.get("")
async def monitors(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    report_id: UUID | None = None,
    version_number: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> AnnotationMonitorsOut:
    await validate_request_session(container, claims)
    values, total = await container.annotation_monitors(session).page(
        claims, report_id, version_number, limit, offset
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationMonitorsOut(
        items=[AnnotationMonitorOut.from_monitor(v) for v in values],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{monitor_id}")
async def monitor(
    monitor_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> AnnotationMonitorOut:
    await validate_request_session(container, claims)
    result = await container.annotation_monitors(session).get(claims, monitor_id)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationMonitorOut.from_monitor(result)


@router.patch("/{monitor_id}")
async def update_monitor(
    monitor_id: UUID,
    body: AnnotationMonitorUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> AnnotationMonitorOut:
    await validate_request_session(container, claims)
    result = await container.annotation_monitors(session).update(
        claims,
        monitor_id,
        body.expected_revision,
        body.action,
        body.name,
        tuple(body.categories) if body.categories is not None else None,
        body.notify_on_change,
        body.rebaseline,
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationMonitorOut.from_monitor(result)


@router.get("/{monitor_id}/transitions")
async def transitions(
    monitor_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> AnnotationTransitionsOut:
    await validate_request_session(container, claims)
    values, total = await list_transitions(
        container.annotation_monitors(session), claims, monitor_id, limit, offset
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationTransitionsOut(
        items=[AnnotationTransitionOut.from_transition(v) for v in values],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{monitor_id}/transitions/{transition_id}")
async def transition(
    monitor_id: UUID,
    transition_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> AnnotationTransitionDetailOut:
    await validate_request_session(container, claims)
    metadata, comparison, _ = await retained_transition(
        container.annotation_monitors(session), claims, monitor_id, transition_id
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationTransitionDetailOut(
        transition=AnnotationTransitionOut.from_transition(metadata), comparison=comparison
    )


@router.post("/{monitor_id}/transitions/{transition_id}/export", response_class=Response)
async def export_transition(
    monitor_id: UUID,
    transition_id: UUID,
    body: AnnotationTransitionExportIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    await validate_request_session(container, claims)
    _, _, payload = await retained_transition(
        container.annotation_monitors(session),
        claims,
        monitor_id,
        transition_id,
        body.expected_comparison_sha256,
    )
    validate_request_expiry(container, claims)
    return Response(
        payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="transition-{transition_id}.json"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{monitor_id}", status_code=204, response_class=Response)
async def delete_monitor(
    monitor_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    expected_revision: Annotated[int, Query(ge=1)],
) -> Response:
    await validate_request_session(container, claims)
    await container.annotation_monitors(session).delete(claims, monitor_id, expected_revision)
    validate_request_expiry(container, claims)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})
