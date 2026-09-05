"""LLM profile administration (admin only)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_llm import (
    LlmProfileIn,
    LlmProfileOut,
    LlmProfilesOut,
    LlmTestOut,
    LlmUsageOut,
    LlmUsagePageOut,
)

router = APIRouter(prefix="/admin/llm", tags=["admin"])


@router.get("/profiles")
async def list_profiles(
    admin: AdminUser, session: SessionDep, container: ContainerDep
) -> LlmProfilesOut:
    profiles = await container.list_llm_profiles(session).execute(admin)
    return LlmProfilesOut(
        items=[LlmProfileOut.from_profile(profile) for profile in profiles],
        encryption_available=container.cipher.available,
    )


@router.post("/profiles", status_code=201)
async def create_profile(
    body: LlmProfileIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> LlmProfileOut:
    profile = await container.create_llm_profile(session).execute(admin, body.to_input(), context)
    return LlmProfileOut.from_profile(profile)


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: UUID,
    body: LlmProfileIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> LlmProfileOut:
    profile = await container.update_llm_profile(session).execute(
        admin, profile_id, body.to_input(), context
    )
    return LlmProfileOut.from_profile(profile)


@router.delete("/profiles/{profile_id}", status_code=204, response_class=Response)
async def delete_profile(
    profile_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.delete_llm_profile(session).execute(admin, profile_id, context)
    return Response(status_code=204)


@router.post("/profiles/{profile_id}/test")
async def test_profile(
    profile_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> LlmTestOut:
    outcome = await container.test_llm_profile(session).execute(admin, profile_id, context)
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
