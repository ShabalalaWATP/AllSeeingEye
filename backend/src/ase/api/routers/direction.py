"""Direction: areas of interest and collection plans with the evidence gathered against them."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_direction import (
    AoiIn,
    AoiOut,
    AoisOut,
    PlanEvidenceOut,
    PlanIn,
    PlanMapMatchesOut,
    PlanOut,
    PlansOut,
    PlanUpdateIn,
)
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/direction", tags=["direction"])


@router.get("/aois")
async def list_aois(user: CurrentUser, session: SessionDep, container: ContainerDep) -> AoisOut:
    areas = await container.list_aois(session).execute(user)
    return AoisOut(items=[AoiOut.from_area(area) for area in areas])


@router.post("/aois", status_code=201)
async def create_aoi(
    body: AoiIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> AoiOut:
    area = await container.create_aoi(session).execute(user, body.to_input(), context)
    return AoiOut.from_area(area)


@router.delete("/aois/{aoi_id}", status_code=204, response_class=Response)
async def delete_aoi(
    aoi_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_aoi(session).execute(user, aoi_id, context)
    return Response(status_code=204)


@router.get("/plans")
async def list_plans(user: CurrentUser, session: SessionDep, container: ContainerDep) -> PlansOut:
    plans = await container.list_plans(session).execute(user)
    return PlansOut(items=[PlanOut.from_plan(plan) for plan in plans])


@router.post("/plans", status_code=201)
async def create_plan(
    body: PlanIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> PlanOut:
    plan = await container.create_plan(session).execute(user, body.to_input(), context)
    return PlanOut.from_plan(plan)


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: UUID, user: CurrentUser, session: SessionDep, container: ContainerDep
) -> PlanEvidenceOut:
    evidence = await container.plan_evidence(session).execute(user, plan_id)
    return PlanEvidenceOut.from_evidence(evidence)


@router.get("/plans/{plan_id}/definition")
async def get_plan_definition(
    plan_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> PlanOut:
    """The plan's requirements and revision without gathering live evidence."""
    plan = await container.plan_definition(session).execute(user, plan_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(PlanOut.from_plan(plan), session=session)


@router.get("/plans/{plan_id}/map-matches")
async def get_plan_map_matches(
    plan_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> PlanMapMatchesOut:
    """Event ids and SIR codes for one reader's map filter; never cached or streamed."""
    result = await container.plan_map_matches(session).execute(user, plan_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(PlanMapMatchesOut.from_matches(result), session=session)


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: UUID,
    body: PlanUpdateIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> PlanOut:
    plan = await container.update_plan(session).execute(
        user, plan_id, body.to_input(), body.expected_updated_at, context
    )
    return PlanOut.from_plan(plan)


@router.delete("/plans/{plan_id}", status_code=204, response_class=Response)
async def delete_plan(
    plan_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_plan(session).execute(user, plan_id, context)
    return Response(status_code=204)
