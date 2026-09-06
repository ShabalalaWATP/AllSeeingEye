"""Authenticated raw document intake with admission before bounded body consumption."""

import asyncio
from collections.abc import Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.errors import PayloadTooLarge
from ase.api.schemas_research_inputs import ResearchInputOut
from ase.api.session_guard import validate_request_session
from ase.application.ports.research_inputs import MAX_INPUT_BYTES, ResearchInputReceipt
from ase.domain.errors import InvalidRequest

router = APIRouter(prefix="/research/inputs", tags=["research"])
BODY_TIMEOUT_SECONDS = 30


async def _wait_for_disconnect(request: Request) -> None:
    while (await request.receive())["type"] != "http.disconnect":
        pass


async def _complete_connected(
    request: Request, operation: Coroutine[Any, Any, ResearchInputReceipt]
) -> ResearchInputReceipt:
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
    claims: ClaimsDep,
    request: Request,
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
        await validate_request_session(container, claims)

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
