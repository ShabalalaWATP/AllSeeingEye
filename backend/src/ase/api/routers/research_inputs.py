"""Authenticated raw document intake with admission before bounded body consumption."""

import asyncio
from collections.abc import Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.errors import PayloadTooLarge
from ase.api.schemas_input_declarations import (
    InputDeclarationsIn,
    InputDeclarationTargetOut,
    InputDeclarationTargetsOut,
)
from ase.api.schemas_photo_geolocation import PhotoGeolocationIn, PhotoGeolocationOut
from ase.api.schemas_research_inputs import ResearchInputOut
from ase.api.session_fence import FenceDep
from ase.application.ports.research_inputs import MAX_INPUT_BYTES
from ase.domain.errors import InvalidRequest

router = APIRouter(prefix="/research/inputs", tags=["research"])
BODY_TIMEOUT_SECONDS = 30


@router.delete("/{input_id}", status_code=204)
async def discard_input(
    input_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> Response:
    async def check_session() -> None:
        await fence.confirm()

    await container.import_research_input(session).discard(
        user,
        input_id,
        before_discard=check_session,
    )
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})


@router.post("/{input_id}/geolocation", status_code=201)
async def geolocate_photo(
    input_id: UUID,
    body: PhotoGeolocationIn,
    user: CurrentUser,
    request: Request,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> PhotoGeolocationOut:
    async def check_session() -> None:
        await fence.confirm()

    result = await _complete_connected(
        request,
        container.photo_geolocation(session).execute(
            user,
            input_id,
            additional_input_ids=tuple(body.additional_input_ids),
            question=body.question,
            hints=body.hints,
            team_id=body.team_id,
            captured_at=body.captured_at,
            consent_to_send_image=body.consent_to_send_image,
            check_session=check_session,
        ),
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return PhotoGeolocationOut(
        **result.assessment.model_dump(),
        provenance=result.provenance,
        input=ResearchInputOut.from_receipt(result.receipt),
        sun_checks=list(result.sun_checks),
    )


@router.get("/{input_id}/declaration-targets")
async def declaration_targets(
    input_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> InputDeclarationTargetsOut:
    async def before_release() -> None:
        await fence.confirm()

    stored = await container.import_research_input(session).declaration_targets(
        user,
        input_id,
        before_release=before_release,
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return InputDeclarationTargetsOut(
        input_id=input_id,
        sha256=stored.receipt.sha256,
        expires_at=stored.receipt.expires_at,
        targets=[
            InputDeclarationTargetOut(
                event_id=event.id,
                content_hash=event.content_hash,
                title=event.title,
                summary=event.summary,
                language=event.language,
                transformations=list(event.transformations),
                source_dates=list(event.source_dates),
            )
            for event in stored.events
        ],
    )


@router.post("/{input_id}/declarations", status_code=201)
async def declare_input(
    input_id: UUID,
    body: InputDeclarationsIn,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
) -> ResearchInputOut:
    service = container.import_research_input(session)

    async def before_retain() -> None:
        await fence.confirm()

    try:
        declarations = tuple(row.to_domain() for row in body.declarations)
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from None
    receipt = await service.declare(
        user, input_id, body.sha256, declarations, before_retain=before_retain
    )
    released = await service.declaration_targets(user, receipt.id, before_release=before_retain)
    fence.assert_live()
    return ResearchInputOut.from_receipt(released.receipt, released.frames)


async def _wait_for_disconnect(request: Request) -> None:
    while (await request.receive())["type"] != "http.disconnect":
        pass


async def _complete_connected[T](request: Request, operation: Coroutine[Any, Any, T]) -> T:
    """ASGI does not cancel a handler automatically when the client abandons a parsed body."""
    work = asyncio.create_task(operation)
    disconnected = asyncio.create_task(_wait_for_disconnect(request))
    try:
        done, _ = await asyncio.wait((work, disconnected), return_when=asyncio.FIRST_COMPLETED)
        if disconnected in done:
            raise asyncio.CancelledError()
        return await work
    finally:
        for task in (work, disconnected):
            if not task.done():
                task.cancel()
        # Waiting is essential: the isolated runner reaps its process and cleans
        # its own temporary directory before the request releases its admission.
        await asyncio.gather(work, disconnected, return_exceptions=True)


@router.post(
    "",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary", "maxLength": MAX_INPUT_BYTES}
                }
            },
        }
    },
)
async def import_input(
    user: CurrentUser,
    request: Request,
    fence: FenceDep,
    session: SessionDep,
    container: ContainerDep,
    filename: Annotated[str, Query(min_length=1, max_length=120)],
) -> ResearchInputOut:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != (
        "application/octet-stream"
    ):
        raise InvalidRequest("Send document bytes as application/octet-stream.")
    service = container.import_research_input(session)

    async def before_retain() -> None:
        await fence.confirm()

    reservation = await service.reserve(user, filename)
    body = bytearray()
    try:
        try:
            async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_INPUT_BYTES:
                        raise PayloadTooLarge()
                    body.extend(chunk)
        except TimeoutError:
            raise InvalidRequest("The document upload timed out.") from None
        data = bytes(body)
        body.clear()
        receipt = await _complete_connected(
            request, service.execute_reserved(user, reservation, data, before_retain=before_retain)
        )
        return ResearchInputOut.from_receipt(receipt, service.previews(user, receipt.id))
    finally:
        body.clear()
        service.release(reservation)
