"""Warning: indicators over the live picture and the alerts they raise."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_warning import AlertOut, AlertsOut, IndicatorIn, IndicatorOut, IndicatorsOut

router = APIRouter(prefix="/warning", tags=["warning"])


@router.get("/indicators")
async def list_indicators(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> IndicatorsOut:
    items = await container.list_indicators(session).execute(user)
    return IndicatorsOut(items=[IndicatorOut.from_indicator(item) for item in items])


@router.post("/indicators", status_code=201)
async def create_indicator(
    body: IndicatorIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> IndicatorOut:
    created = await container.create_indicator(session).execute(user, body.to_input(), context)
    return IndicatorOut.from_indicator(created)


@router.put("/indicators/{indicator_id}")
async def update_indicator(
    indicator_id: UUID,
    body: IndicatorIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> IndicatorOut:
    updated = await container.update_indicator(session).execute(
        user, indicator_id, body.to_input(), context
    )
    return IndicatorOut.from_indicator(updated)


@router.delete("/indicators/{indicator_id}", status_code=204, response_class=Response)
async def delete_indicator(
    indicator_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_indicator(session).execute(user, indicator_id, context)
    return Response(status_code=204)


@router.get("/alerts")
async def list_alerts(
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    hours: Annotated[int | None, Query(ge=1, le=720)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AlertsOut:
    items = await container.list_alerts(session).execute(user, hours=hours, limit=limit)
    return AlertsOut(
        items=[AlertOut.from_alert(item) for item in items],
        unacknowledged=sum(1 for item in items if item.acknowledged_at is None),
    )


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AlertOut:
    alert = await container.acknowledge_alert(session).execute(user, alert_id, context)
    return AlertOut.from_alert(alert)
