"""Scheduled products: standing orders for reports."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.adapters.persistence.subscription_briefs import load_brief_revision
from ase.adapters.persistence.subscription_comparisons import (
    SqlSubscriptionComparisonRepository,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.errors import InvalidQuery
from ase.api.routers.schedule_activation import router as activation_router
from ase.api.routers.subscription_controls import router as edition_controls_router
from ase.api.schemas_schedules import (
    ScheduleFromBriefIn,
    ScheduleIn,
    ScheduleOccurrenceOut,
    ScheduleOut,
    SchedulePreviewOut,
    SchedulesOut,
)
from ase.api.schemas_subscription_editions import (
    RunNowIn,
    SubscriptionEditionOut,
    SubscriptionEditionsOut,
    SubscriptionEventOut,
    SubscriptionEventsOut,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.definition import ScheduleInput
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.container.subscription_schedule_controls import archive_schedule
from ase.domain.errors import NotFound
from ase.domain.research_brief_values import BriefValidationError
from ase.domain.subscription_recurrence import LocalRecurrence

router = APIRouter(prefix="/schedules", tags=["schedules"])
router.include_router(edition_controls_router)
router.include_router(activation_router)


@router.post("/{schedule_id}/run-now", status_code=202)
async def run_subscription_now(
    schedule_id: UUID,
    body: RunNowIn,
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> SubscriptionEditionOut:
    await validate_request_session(container, claims)
    edition = await SubscriptionAdmission(container).run_now(
        schedule_id,
        body.request_id,
        user,
        context,
        lambda guarded: validate_request_session(container, claims, session=guarded),
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionEditionOut.from_edition(edition)


@router.post("/preview")
async def preview_schedule(
    body: ScheduleIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SchedulePreviewOut:
    access = await container.access_policy(session).context(user)
    access.require_create(body.team_id)
    try:
        recurrence = LocalRecurrence(
            body.timezone,
            body.hour_utc if body.local_hour is None else body.local_hour,
            body.local_minute,
            body.cadence,
            body.weekday,
            body.monthday,
            body.anchor_month,
        )
        occurrences = recurrence.preview(container.clock.now(), 3)
    except ValueError as exc:
        raise InvalidQuery("Invalid schedule preview.", fields={"recurrence": str(exc)}) from exc
    await validate_request_session(container, claims, session=session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SchedulePreviewOut(
        next_three=[
            ScheduleOccurrenceOut(
                scheduled_date=row.scheduled_date.isoformat(),
                local=row.local,
                utc=row.utc,
                dst_resolution=row.dst_resolution,
            )
            for row in occurrences
        ],
        collection_policy=body.collection_policy,
        window_hours=body.window_hours,
    )


@router.get("/{schedule_id}/editions")
async def list_subscription_editions(
    schedule_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SubscriptionEditionsOut:
    access = await container.access_policy(session).context(user)
    schedule = await container.repositories(session).schedules.get(schedule_id)
    if schedule is None:
        raise NotFound("Subscription not found.")
    access.require_read(schedule.created_by, schedule.team_id)
    repository = SqlSubscriptionEditionRepository(session)
    editions = await repository.history(schedule_id, limit=limit, offset=offset)
    comparisons = await SqlSubscriptionComparisonRepository(session).list_for(
        [edition.id for edition in editions]
    )
    result = SubscriptionEditionsOut(
        items=[
            SubscriptionEditionOut.from_edition(edition, comparisons.get(edition.id))
            for edition in editions
        ],
        limit=limit,
        offset=offset,
    )
    await validate_request_session(container, claims, session=session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{schedule_id}/events")
async def list_subscription_events(
    schedule_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SubscriptionEventsOut:
    access = await container.access_policy(session).context(user)
    schedule = await container.repositories(session).schedules.get(schedule_id)
    if schedule is None:
        raise NotFound("Subscription not found.")
    access.require_read(schedule.created_by, schedule.team_id)
    deliveries = await SqlSubscriptionEditionRepository(session).in_app_events(
        schedule_id, limit=limit, offset=offset
    )
    result = SubscriptionEventsOut(
        items=[SubscriptionEventOut.from_delivery(item) for item in deliveries],
        limit=limit,
        offset=offset,
    )
    await validate_request_session(container, claims, session=session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("")
async def list_schedules(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SchedulesOut:
    items = await container.list_schedules(session).execute(user)
    await validate_request_session(container, claims, session=session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SchedulesOut(items=[ScheduleOut.from_schedule(item) for item in items])


@router.post("", status_code=201)
async def create_schedule(
    body: ScheduleIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    await validate_request_session(container, claims, session=session)
    created = await container.create_schedule(session).execute(
        user,
        body.to_input(),
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ScheduleOut.from_schedule(created)


@router.post("/from-brief", status_code=201)
async def create_schedule_from_brief(
    body: ScheduleFromBriefIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    await validate_request_session(container, claims, session=session)
    access = await container.access_policy(session).context(user, for_update=True)
    brief = await load_brief_revision(session, access, body.brief_id, body.brief_revision)
    access.require_same_scope(
        user.id, brief.identity.team_id, brief.identity.owner_id, brief.identity.team_id
    )
    access.require_create(brief.identity.team_id)
    try:
        request = standing_request_from_brief(brief, now=container.clock.now())
    except BriefValidationError as exc:
        raise InvalidQuery(
            "The Research Brief cannot be subscribed to.",
            fields={exc.field: "Invalid or unsupported value."},
        ) from exc
    data = ScheduleInput(
        name=body.name or brief.identity.title,
        template_id=request.template_id,
        country_iso=request.country_iso,
        country_isos=request.country_isos,
        plan_id=request.plan_id,
        hour_utc=body.local_hour,
        timezone=body.timezone,
        local_hour=body.local_hour,
        local_minute=body.local_minute,
        cadence=body.cadence,
        weekday=body.weekday,
        monthday=body.monthday,
        anchor_month=body.anchor_month,
        collection_policy=body.collection_policy,
        window_hours=request.window_hours,
        enabled=body.enabled,
        team_id=brief.identity.team_id,
        notify_on_change=body.notify_on_change,
        avoid_repetition=body.avoid_repetition,
        question=request.question,
        research_mode=request.research_mode,
        research_languages=request.research_languages,
        research_focus=request.research_focus,
        research_subject=request.research_subject,
        research_web_search=request.research_web_search,
        research_source_ids=request.research_source_ids,
        conflict_id=request.conflict_id,
        hazard=request.hazard,
        research_area=request.research_area,
        disclose_area_to_provider=request.disclose_area_to_provider,
        brief_id=body.brief_id,
        brief_revision=body.brief_revision,
    )
    created = await container.create_schedule(session).execute(
        user,
        data,
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    await validate_request_session(container, claims, session=session)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ScheduleOut.from_schedule(created)


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: UUID,
    body: ScheduleIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    await validate_request_session(container, claims, session=session)
    updated = await container.update_schedule(session).execute(
        user,
        schedule_id,
        body.to_input(),
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ScheduleOut.from_schedule(updated)


@router.delete("/{schedule_id}", status_code=204, response_class=Response)
async def delete_schedule(
    schedule_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> Response:
    await validate_request_session(container, claims, session=session)
    await archive_schedule(
        container,
        session,
        user,
        schedule_id,
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})
