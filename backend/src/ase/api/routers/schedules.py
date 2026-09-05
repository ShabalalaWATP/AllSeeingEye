"""Scheduled products: standing orders for reports."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_schedules import ScheduleIn, ScheduleOut, SchedulesOut

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> SchedulesOut:
    items = await container.list_schedules(session).execute(user)
    return SchedulesOut(items=[ScheduleOut.from_schedule(item) for item in items])


@router.post("", status_code=201)
async def create_schedule(
    body: ScheduleIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> ScheduleOut:
    created = await container.create_schedule(session).execute(user, body.to_input(), context)
    return ScheduleOut.from_schedule(created)


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: UUID,
    body: ScheduleIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> ScheduleOut:
    updated = await container.update_schedule(session).execute(
        user, schedule_id, body.to_input(), context
    )
    return ScheduleOut.from_schedule(updated)


@router.delete("/{schedule_id}", status_code=204, response_class=Response)
async def delete_schedule(
    schedule_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_schedule(session).execute(user, schedule_id, context)
    return Response(status_code=204)
