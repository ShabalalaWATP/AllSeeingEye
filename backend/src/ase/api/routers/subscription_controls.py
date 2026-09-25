"""Edition controls expose the existing retained-job transitions within schedule scope."""

from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_subscription_editions import SubscriptionBaselineOut, SubscriptionEditionOut
from ase.api.session_fence import FenceDep, SessionFence
from ase.container import Container
from ase.container.subscription_baseline_control import accept_baseline
from ase.container.subscription_edition_controls import EditionControl, control_edition
from ase.domain.users import User

router = APIRouter(tags=["schedules"])


async def _control(
    schedule_id: UUID,
    edition_id: UUID,
    action: EditionControl,
    user: User,
    fence: SessionFence,
    session: AsyncSession,
    container: Container,
    response: Response,
) -> SubscriptionEditionOut:
    current = await control_edition(
        container,
        session,
        user,
        schedule_id,
        edition_id,
        action,
        check_session=lambda: fence.confirm(session=session),
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionEditionOut.from_edition(current)


@router.post("/{schedule_id}/editions/{edition_id}/pause")
async def pause_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "pause", user, fence, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/resume", status_code=202)
async def resume_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "resume", user, fence, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/retry", status_code=202)
async def retry_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "retry", user, fence, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/accept-baseline")
async def accept_edition_baseline(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> SubscriptionBaselineOut:
    lineage = await accept_baseline(
        container,
        session,
        user,
        schedule_id,
        edition_id,
        context,
        check_session=lambda: fence.confirm(session=session),
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionBaselineOut.from_lineage(lineage, edition_id)
