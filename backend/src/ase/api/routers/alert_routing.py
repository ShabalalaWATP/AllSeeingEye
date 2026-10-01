"""Explicit export settings, with object-level authority and fenced responses."""

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_alert_routing import (
    AlertDestinationIn,
    AlertDestinationsOut,
    AlertRoutingCapabilitiesOut,
    AlertRoutingIn,
    AlertRoutingOut,
    AlertWebhookDestinationOut,
)
from ase.api.session_fence import FenceDep
from ase.container.alert_routing import alert_routing

router = APIRouter(prefix="/warning", tags=["alert-routing"])


@router.get("/notification-capabilities", response_model=AlertRoutingCapabilitiesOut)
async def notification_capabilities(
    actor: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
) -> AlertRoutingCapabilitiesOut:
    return await fence.release(
        AlertRoutingCapabilitiesOut(
            installation_copy_enabled=bool(container.settings.alert_webhook_url),
        )
    )


@router.get("/indicators/{indicator_id}/notifications", response_model=AlertRoutingOut)
async def get_alert_route(
    indicator_id: UUID,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
) -> AlertRoutingOut:
    route, can_manage = await alert_routing(container, session).get(actor, indicator_id)
    return await fence.release(
        AlertRoutingOut(**asdict(route), can_manage=can_manage), session=session
    )


@router.put("/indicators/{indicator_id}/notifications", response_model=AlertRoutingOut)
async def save_alert_route(
    indicator_id: UUID,
    body: AlertRoutingIn,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    context: ContextDep,
) -> AlertRoutingOut:
    route = await alert_routing(container, session).save(
        actor,
        indicator_id,
        email_enabled=body.email_enabled,
        webhook_id=body.webhook_id,
        expected_revision=body.expected_revision,
        context=context,
    )
    return await fence.release(AlertRoutingOut(**asdict(route), can_manage=True), session=session)


@router.get("/webhook-destinations", response_model=AlertDestinationsOut)
async def list_webhook_destinations(
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    team_id: UUID | None = None,
) -> AlertDestinationsOut:
    items = await alert_routing(container, session).destinations(actor, team_id)
    return await fence.release(
        AlertDestinationsOut(
            items=[AlertWebhookDestinationOut.model_validate(item) for item in items],
        ),
        session=session,
    )


@router.post("/webhook-destinations", status_code=201, response_model=AlertWebhookDestinationOut)
async def register_webhook_destination(
    body: AlertDestinationIn,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    context: ContextDep,
) -> AlertWebhookDestinationOut:
    destination = await alert_routing(container, session).register_destination(
        actor,
        body.name,
        body.url.get_secret_value(),
        body.team_id,
        context,
    )
    return await fence.release(
        AlertWebhookDestinationOut.model_validate(destination), session=session
    )


@router.delete("/webhook-destinations/{destination_id}", status_code=204)
async def remove_webhook_destination(
    destination_id: UUID,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    context: ContextDep,
) -> Response:
    await alert_routing(container, session).remove_destination(actor, destination_id, context)
    return await fence.release(Response(status_code=204), session=session)
