"""Edition controls expose the existing retained-job transitions within schedule scope."""

from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_subscription_editions import SubscriptionBaselineOut, SubscriptionEditionOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.dto import AccessClaims
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
    claims: AccessClaims,
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
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionEditionOut.from_edition(current)


@router.post("/{schedule_id}/editions/{edition_id}/pause")
async def pause_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "pause", user, claims, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/resume", status_code=202)
async def resume_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "resume", user, claims, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/retry", status_code=202)
async def retry_edition(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> SubscriptionEditionOut:
    return await _control(
        schedule_id, edition_id, "retry", user, claims, session, container, response
    )


@router.post("/{schedule_id}/editions/{edition_id}/accept-baseline")
async def accept_edition_baseline(
    schedule_id: UUID,
    edition_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
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
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return SubscriptionBaselineOut.from_lineage(lineage, edition_id)
