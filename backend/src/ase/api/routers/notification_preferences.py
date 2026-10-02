"""Explicit, current-account opt-ins for external subscription mail."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_notifications import (
    EmailPreferencesIn,
    EmailPreferencesOut,
    SubscriptionEmailIn,
)
from ase.api.session_fence import FenceDep
from ase.container.notifications import notification_preferences, notification_sender
from ase.domain.notification_delivery import EmailPreferences, SubscriptionEmailPreferences

router = APIRouter(tags=["notifications"])


@router.get("/me/notifications/email", response_model=EmailPreferencesOut)
async def email_preferences(
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> EmailPreferencesOut:
    response.headers["Cache-Control"] = "private, no-store"
    preferences, confirmed = await notification_preferences(container, session).email(actor)
    result = EmailPreferencesOut(
        enabled=preferences.enabled,
        include_names=preferences.include_names,
        available=notification_sender(container).available,
        confirmed=confirmed,
        destination=actor.email,
    )
    return await fence.release(result, session=session)


@router.put("/me/notifications/email", status_code=204)
async def save_email_preferences(
    body: EmailPreferencesIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    await notification_preferences(container, session).save_email(
        actor,
        EmailPreferences(body.enabled, body.include_names),
    )
    return await fence.release(Response(status_code=204), session=session)


@router.get("/schedules/{subscription_id}/notifications/email", response_model=SubscriptionEmailIn)
async def subscription_email_preferences(
    subscription_id: UUID,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> SubscriptionEmailIn:
    preferences = await notification_preferences(container, session).subscription(
        actor, subscription_id
    )
    return await fence.release(SubscriptionEmailIn.model_validate(preferences), session=session)


@router.put("/schedules/{subscription_id}/notifications/email", status_code=204)
async def save_subscription_email_preferences(
    subscription_id: UUID,
    body: SubscriptionEmailIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    await notification_preferences(container, session).save_subscription(
        actor,
        subscription_id,
        SubscriptionEmailPreferences(body.policy, body.attention),
    )
    return await fence.release(Response(status_code=204), session=session)
