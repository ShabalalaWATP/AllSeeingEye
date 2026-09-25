"""LLM profile administration (admin only)."""

from __future__ import annotations

from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_llm import (
    LlmConnectionIn,
    LlmConnectionOut,
    LlmConnectionsOut,
    LlmModelsOut,
    LlmProfileIn,
    LlmProfileOut,
    LlmProfilesOut,
    LlmTestOut,
    LlmUsageOut,
    LlmUsagePageOut,
)
from ase.api.schemas_llm_workspace import LlmWorkspaceIn, LlmWorkspaceOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/admin/llm", tags=["admin"])


@router.put("/workspace")
async def update_workspace(
    body: LlmWorkspaceIn,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
) -> LlmWorkspaceOut:
    result = await container.llm_workspace(session).execute(
        admin,
        [change.to_input() for change in body.changes],
        context,
        before_save=partial(fence.confirm, session=session, admin_only=True),
    )
    return LlmWorkspaceOut.from_result(result)


@router.get("/profiles")
async def list_profiles(
    admin: AdminUser, session: SessionDep, container: ContainerDep
) -> LlmProfilesOut:
    profiles = await container.list_llm_profiles(session).execute(admin)
    bindings = await container.llm_connections(session).list(admin)
    bound_ids = {binding.profile_id for binding in bindings}
    return LlmProfilesOut(
        items=[
            LlmProfileOut.from_profile(profile, is_bound=profile.id in bound_ids)
            for profile in profiles
        ],
        encryption_available=container.cipher.available,
    )


@router.post("/profiles", status_code=201)
async def create_profile(
    body: LlmProfileIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
) -> LlmProfileOut:
    profile = await container.create_llm_profile(session).execute(
        admin,
        body.to_input(),
        context,
        before_save=fence.confirm,
    )
    return LlmProfileOut.from_profile(profile)


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: UUID,
    body: LlmProfileIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
) -> LlmProfileOut:
    profile = await container.update_llm_profile(session).execute(
        admin,
        profile_id,
        body.to_input(),
        context,
        before_save=fence.confirm,
    )
    return LlmProfileOut.from_profile(profile)


@router.delete("/profiles/{profile_id}", status_code=204, response_class=Response)
async def delete_profile(
    profile_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
) -> Response:
    await container.delete_llm_profile(session).execute(
        admin, profile_id, context, before_save=fence.confirm
    )
    return Response(status_code=204)


@router.post("/profiles/{profile_id}/test")
async def test_profile(
    profile_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
) -> LlmTestOut:
    outcome = await container.test_llm_profile(session).execute(
        admin, profile_id, context, before_save=fence.confirm
    )
    return LlmTestOut.from_outcome(outcome)


@router.get("/usage")
async def list_usage(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> LlmUsagePageOut:
    usage = await container.list_llm_usage(session).execute(admin, limit)
    return LlmUsagePageOut(items=[LlmUsageOut.from_usage(item) for item in usage])


@router.get("/profiles/{profile_id}/models")
async def discover_models(
    profile_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> LlmModelsOut:
    models = await container.discover_llm_models(session).execute(
        admin, profile_id, before_return=fence.confirm
    )
    return LlmModelsOut(models=list(models))


@router.get("/connections")
async def list_connections(
    admin: AdminUser, session: SessionDep, container: ContainerDep
) -> LlmConnectionsOut:
    bindings = await container.llm_connections(session).list(admin)
    return LlmConnectionsOut(items=[LlmConnectionOut.from_binding(item) for item in bindings])


@router.put("/connections")
async def activate_connection(
    body: LlmConnectionIn,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
) -> LlmConnectionOut:
    binding = await container.llm_connections(session).activate(
        admin,
        body.to_input(),
        context,
        before_save=fence.confirm,
    )
    return LlmConnectionOut.from_binding(binding)


@router.delete("/connections/team/{team_id}", status_code=204, response_class=Response)
async def reset_team_connection(
    team_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
    expected_revision: Annotated[int, Query(ge=1)],
) -> Response:
    await container.llm_connections(session).reset_team(
        admin,
        team_id,
        expected_revision,
        context,
        before_save=fence.confirm,
    )
    return Response(status_code=204)


@router.delete("/connections/user/{user_id}", status_code=204, response_class=Response)
async def reset_user_connection(
    user_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
    expected_revision: Annotated[int, Query(ge=1)],
) -> Response:
    await container.llm_connections(session).reset_user(
        admin,
        user_id,
        expected_revision,
        context,
        before_save=fence.confirm,
    )
    return Response(status_code=204)
