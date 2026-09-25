"""Authenticated, opt-in operator directory and the current user's directory profile."""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.errors import PayloadTooLarge
from ase.api.schemas_directory_profile import (
    DirectoryPageOut,
    DirectoryProfileOut,
    DirectoryProfileUpdateIn,
)
from ase.api.session_fence import FenceDep
from ase.domain.directory_avatar import MAX_AVATAR_UPLOAD_BYTES
from ase.domain.errors import InvalidRequest

router = APIRouter(tags=["directory"])
AVATAR_UPLOAD_TIMEOUT_SECONDS = 30
AVATAR_CACHE_SECONDS = 300


@router.get("/directory/users", response_model=DirectoryPageOut)
async def search_directory(
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    q: Annotated[str, Query(min_length=2, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> DirectoryPageOut:
    page = await container.directory_profile(session).search(actor, q, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return DirectoryPageOut.from_page(page)


@router.get("/me/directory-profile", response_model=DirectoryProfileOut)
async def get_directory_profile(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> DirectoryProfileOut:
    profile = await container.directory_profile(session).get(claims)
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)


@router.patch("/me/directory-profile", response_model=DirectoryProfileOut)
async def update_directory_profile(
    body: DirectoryProfileUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> DirectoryProfileOut:
    profile = await container.directory_profile(session).update(
        claims,
        body.to_changes(),
        body.expected_revision,
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)


@router.put(
    "/me/directory-profile/avatar",
    response_model=DirectoryProfileOut,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "maxLength": MAX_AVATAR_UPLOAD_BYTES,
                    }
                }
            },
        }
    },
)
async def upload_directory_avatar(
    request: Request,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> DirectoryProfileOut:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/octet-stream"
        or request.headers.get("content-encoding", "identity").lower() != "identity"
    ):
        raise InvalidRequest("Send unencoded avatar bytes as application/octet-stream.")
    # Authenticate against the current account before accepting any body bytes.
    await fence.confirm()
    body = bytearray()
    try:
        try:
            async with asyncio.timeout(AVATAR_UPLOAD_TIMEOUT_SECONDS):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_AVATAR_UPLOAD_BYTES:
                        raise PayloadTooLarge()
                    body.extend(chunk)
        except TimeoutError:
            raise InvalidRequest("The avatar upload timed out.") from None
        profile = await container.directory_avatar(session).upload(claims, bytes(body), context)
    finally:
        body.clear()
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)


@router.delete("/me/directory-profile/avatar", response_model=DirectoryProfileOut)
async def remove_directory_avatar(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> DirectoryProfileOut:
    profile = await container.directory_avatar(session).remove(claims, context)
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)


@router.get(
    "/directory/users/{user_id}/avatar",
    response_class=Response,
    responses={200: {"content": {"image/webp": {}, "image/png": {}}}},
)
async def get_directory_avatar(
    user_id: UUID,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    avatar = await container.directory_avatar(session).read(actor, user_id)
    return Response(
        avatar.image.content,
        media_type=avatar.image.content_type,
        headers={
            # Private: visibility depends on the viewer, so shared caches must not keep it.
            "Cache-Control": f"private, max-age={AVATAR_CACHE_SECONDS}",
            "ETag": f'"{avatar.image.sha256}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "Vary": "Authorization",
        },
    )
