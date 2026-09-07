"""Private exact-revision PNG packages with admission before request buffering."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import ValidationError

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.errors import PayloadTooLarge
from ase.api.schemas_map_image import MapImagePackageIn
from ase.application.ports.map_image import MAX_MAP_IMAGE_BODY
from ase.domain.errors import InvalidRequest

router = APIRouter(prefix="/map/views", tags=["maps"])


@router.post(
    "/{view_id}/revisions/{revision_id}/image-package",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": MapImagePackageIn.model_json_schema()}},
        }
    },
)
async def export_image_package(
    view_id: UUID,
    revision_id: UUID,
    request: Request,
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    service = container.export_map_image(session)
    with service.admission():
        selected = await service.resolve(claims, view_id, revision_id)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != (
            "application/json"
        ):
            raise InvalidRequest("Send the map image envelope as application/json.")
        body = bytearray()
        try:
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_MAP_IMAGE_BODY:
                        raise PayloadTooLarge()
                    body.extend(chunk)
            try:
                options = MapImagePackageIn.model_validate_json(body).to_options()
            except ValidationError:
                raise InvalidRequest("Invalid map image export envelope.") from None
        except TimeoutError:
            raise InvalidRequest("The map image upload timed out.") from None
        finally:
            body.clear()
        result = await service.execute(claims, selected, options)
        return Response(
            content=result.content,
            media_type=result.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
