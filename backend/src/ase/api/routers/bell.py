"""The in-app notification bell: scoped summary, destinations, acknowledgement and mutes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_bell import (
    AlertDestinationOut,
    BellAcknowledgeIn,
    BellAcknowledgeOut,
    BellOut,
    BellPreferencesIn,
    BellPreferencesOut,
)
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/bell", tags=["bell"])
NO_STORE = "no-store"


@router.get("")
async def read_bell(
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> BellOut:
    summary = await container.bell(session).summary(user)
    response.headers["Cache-Control"] = NO_STORE
    return await fence.release(BellOut.build(summary), session=session)


@router.get("/alerts/{alert_id}/destination")
async def alert_destination(
    alert_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> AlertDestinationOut:
    destination = await container.bell_alerts(session).destination(user, alert_id)
    response.headers["Cache-Control"] = NO_STORE
    return await fence.release(AlertDestinationOut.build(destination), session=session)


@router.post("/alerts/acknowledge")
async def acknowledge_shown(
    body: BellAcknowledgeIn,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> BellAcknowledgeOut:
    await fence.confirm(session=session)
    outcome = await container.bell_acknowledgements(session).acknowledge(
        user, body.alert_ids, context
    )
    return await fence.release(BellAcknowledgeOut.build(outcome), session=session)


@router.put("/preferences")
async def set_bell_preferences(
    body: BellPreferencesIn,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
) -> BellPreferencesOut:
    await fence.confirm(session=session)
    preferences = await container.bell_preferences(session).set_kinds(user, body.muted_kinds)
    return await fence.release(BellPreferencesOut.build(preferences), session=session)


@router.put("/muted-rules/{indicator_id}")
async def mute_rule(
    indicator_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
) -> BellPreferencesOut:
    await fence.confirm(session=session)
    preferences = await container.bell_preferences(session).mute_rule(user, indicator_id)
    return await fence.release(BellPreferencesOut.build(preferences), session=session)


@router.delete("/muted-rules/{indicator_id}")
async def unmute_rule(
    indicator_id: UUID,
    user: CurrentUser,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
) -> BellPreferencesOut:
    await fence.confirm(session=session)
    preferences = await container.bell_preferences(session).unmute_rule(user, indicator_id)
    return await fence.release(BellPreferencesOut.build(preferences), session=session)
