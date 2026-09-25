"""Whole-subscription controls for normal and exact-brief schedules."""

from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_schedules import ScheduleOut
from ase.api.session_fence import FenceDep, SessionFence
from ase.application.dto import RequestContext
from ase.container import Container
from ase.container.subscription_schedule_controls import control_schedule
from ase.domain.users import User

router = APIRouter(tags=["schedules"])


async def _control(
    schedule_id: UUID,
    enabled: bool,
    user: User,
    fence: SessionFence,
    session: AsyncSession,
    container: Container,
    context: RequestContext,
    response: Response,
) -> ScheduleOut:
    schedule = await control_schedule(
        container,
        session,
        user,
        schedule_id,
        enabled,
        context,
        check_session=lambda: fence.confirm(session=session),
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return ScheduleOut.from_schedule(schedule)


@router.post("/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    return await _control(schedule_id, False, user, fence, session, container, context, response)


@router.post("/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    return await _control(schedule_id, True, user, fence, session, container, context, response)
