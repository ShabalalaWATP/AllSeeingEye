"""Authenticated original bytes, admitted before streaming and served only as attachments."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep
from ase.api.errors import PayloadTooLarge
from ase.api.original_upload import finish_connected
from ase.api.schemas_original_assets import (
    OriginalAssetListOut,
    OriginalAssetOut,
    OriginalAssetReserveIn,
)
from ase.api.session_fence import FenceDep
from ase.domain.errors import InvalidRequest
from ase.domain.original_assets import MAX_ASSET_BYTES

router = APIRouter(prefix="/reports/{report_id}/original-assets", tags=["reports"])
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
UPLOAD_TIMEOUT_SECONDS = 60


@router.get("")
async def list_assets(
    report_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    version_number: Annotated[int, Query(ge=1)],
) -> OriginalAssetListOut:
    assets = await container.original_assets(session).list(claims, report_id, version_number)
    response.headers.update(HEADERS)
    return OriginalAssetListOut(items=[OriginalAssetOut.build(asset) for asset in assets])


@router.post("", status_code=201)
async def reserve_asset(
    report_id: UUID,
    body: OriginalAssetReserveIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> OriginalAssetOut:
    asset = await container.original_assets(session).reserve(claims, report_id, body.to_domain())
    response.headers.update(HEADERS)
    return OriginalAssetOut.build(asset)


@router.put(
    "/{asset_id}/content",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "maxLength": MAX_ASSET_BYTES,
                    }
                },
            },
        }
    },
)
async def upload_asset(
    report_id: UUID,
    asset_id: UUID,
    request: Request,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> OriginalAssetOut:
    if (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != ("application/octet-stream")
        or request.headers.get("content-encoding", "identity").lower() != "identity"
    ):
        raise InvalidRequest("Send unencoded original bytes as application/octet-stream.")
    service = container.original_assets(session)
    asset = await service.begin_upload(claims, report_id, asset_id)
    body = bytearray()
    completed = False
    try:
        try:
            async with asyncio.timeout(UPLOAD_TIMEOUT_SECONDS):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > asset.byte_count:
                        raise PayloadTooLarge()
                    body.extend(chunk)
                saved = await finish_connected(
                    request, service.finish_upload(claims, report_id, asset_id, bytes(body))
                )
        except TimeoutError:
            raise InvalidRequest("The original upload timed out.") from None
        completed = True
        response.headers.update(HEADERS)
        return OriginalAssetOut.build(saved)
    finally:
        body.clear()
        if not completed:
            await session.rollback()
            # Revoked credentials cannot prevent internal reservation cleanup.
            # Crash/forced cancellation is additionally bounded by reservation expiry.
            async with container.session_factory() as cleanup_session:
                await container.original_assets(cleanup_session).abandon_upload(
                    asset_id,
                    claims.user_id,
                )


@router.get("/{asset_id}/content", response_class=Response)
async def download_asset(
    report_id: UUID,
    asset_id: UUID,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    await fence.confirm()
    found = await container.original_assets(session).download(claims, report_id, asset_id)
    return Response(
        found.content,
        media_type="application/octet-stream",
        headers={
            **HEADERS,
            "Content-Disposition": f'attachment; filename="original-{asset_id}.bin"',
        },
    )


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    report_id: UUID,
    asset_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    await container.original_assets(session).delete(claims, report_id, asset_id)
    return Response(status_code=204, headers=HEADERS)
