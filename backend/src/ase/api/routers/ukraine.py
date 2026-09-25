"""Authenticated Ukraine war tracker: the board from the live store, control from the snapshot."""

from fastapi import APIRouter, Response
from fastapi.responses import Response as RawResponse

from ase.api.deps import AdminUser, ContainerDep, ContextDep, CurrentUser
from ase.api.schemas_ukraine import ControlOut, UkraineBoardOut
from ase.api.schemas_ukraine_digest import UkraineDigestOut
from ase.api.schemas_ukraine_frontline import FrontlineOut, SpottedOut
from ase.api.schemas_ukraine_reference import UkraineReferenceOut
from ase.api.session_fence import FenceDep
from ase.domain.errors import NotFound

router = APIRouter(prefix="/conflicts/ukraine", tags=["trackers"])


@router.get("")
async def ukraine_board(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> UkraineBoardOut:
    board = UkraineBoardOut.from_board(container.ukraine().board())
    await fence.confirm()
    response.headers["Cache-Control"] = "private, no-store"
    return board


@router.get("/control")
async def ukraine_control(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> ControlOut:
    """The packaged snapshot changes only when the operator re-imports it."""
    payload = ControlOut.build(container.ukraine_control, container.ukraine_outlines)
    await fence.confirm()
    response.headers["Cache-Control"] = "private, max-age=3600"
    return payload


@router.get("/frontline")
async def ukraine_frontline(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> FrontlineOut:
    """Provider geometry when a flag enables one; otherwise the disabled state and why."""
    payload = FrontlineOut.from_state(await container.ukraine_providers.snapshot())
    await fence.confirm()
    response.headers["Cache-Control"] = "private, max-age=900"
    return payload


@router.get("/spotted")
async def ukraine_spotted(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> SpottedOut:
    """Geolocated visually confirmed losses when the operator has enabled the layer."""
    payload = SpottedOut.from_state(await container.ukraine_providers.spotted())
    await fence.confirm()
    response.headers["Cache-Control"] = "private, max-age=900"
    return payload


@router.get("/digest")
async def ukraine_digest(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> UkraineDigestOut:
    """The fortnightly model digest and the few before it; a reader never forces new spend."""
    view = await container.ukraine_digest.view()
    await fence.confirm()
    response.headers["Cache-Control"] = "private, no-store"
    return UkraineDigestOut.from_view(view)


@router.post("/digest/refresh")
async def refresh_ukraine_digest(
    admin: AdminUser,
    context: ContextDep,
    fence: FenceDep,
    response: Response,
    container: ContainerDep,
) -> UkraineDigestOut:
    """Administrators may ask for a digest before the fortnight is up; audited and limited."""
    await fence.confirm(admin_only=True)
    view = await container.ukraine_digest.refresh(admin, context.ip)
    response.headers["Cache-Control"] = "no-store"
    return UkraineDigestOut.from_view(view)


@router.get("/reference")
async def ukraine_reference(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> UkraineReferenceOut:
    """Curated notes on equipment, forces and the timeline; absent until imported."""
    catalogue = container.ukraine_reference
    if catalogue is None:
        raise NotFound()
    payload = UkraineReferenceOut.from_catalogue(catalogue)
    await fence.confirm()
    response.headers["Cache-Control"] = "private, max-age=3600"
    return payload


@router.get("/images/{image_id}.jpg")
async def ukraine_image(
    image_id: str,
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
) -> RawResponse:
    """A cached Commons image from the packaged store, same origin so the CSP is unchanged."""
    data = container.ukraine_image(image_id)
    if data is None:
        raise NotFound()
    await fence.confirm()
    return RawResponse(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
