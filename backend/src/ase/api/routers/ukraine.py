"""Authenticated Ukraine war tracker: the board from the live store, control from the snapshot."""

from fastapi import APIRouter, Response
from fastapi.responses import Response as RawResponse

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_ukraine import ControlOut, UkraineBoardOut
from ase.api.schemas_ukraine_frontline import FrontlineOut, SpottedOut
from ase.api.schemas_ukraine_reference import UkraineReferenceOut
from ase.api.session_guard import validate_request_session
from ase.domain.errors import NotFound

router = APIRouter(prefix="/conflicts/ukraine", tags=["trackers"])


@router.get("")
async def ukraine_board(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> UkraineBoardOut:
    board = UkraineBoardOut.from_board(container.ukraine().board())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return board


@router.get("/control")
async def ukraine_control(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> ControlOut:
    """The packaged snapshot changes only when the operator re-imports it."""
    payload = ControlOut.build(container.ukraine_control, container.ukraine_outlines)
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return payload


@router.get("/frontline")
async def ukraine_frontline(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> FrontlineOut:
    """Provider geometry when a flag enables one; otherwise the disabled state and why."""
    payload = FrontlineOut.from_state(await container.ukraine_providers.snapshot())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, max-age=900"
    return payload


@router.get("/spotted")
async def ukraine_spotted(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> SpottedOut:
    """Geolocated visually confirmed losses when the operator has enabled the layer."""
    payload = SpottedOut.from_state(await container.ukraine_providers.spotted())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, max-age=900"
    return payload


@router.get("/reference")
async def ukraine_reference(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> UkraineReferenceOut:
    """Curated notes on equipment, forces and the timeline; absent until imported."""
    catalogue = container.ukraine_reference
    if catalogue is None:
        raise NotFound()
    payload = UkraineReferenceOut.from_catalogue(catalogue)
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return payload


@router.get("/images/{image_id}.jpg")
async def ukraine_image(
    image_id: str, user: CurrentUser, claims: ClaimsDep, container: ContainerDep
) -> RawResponse:
    """A cached Commons image from the packaged store, same origin so the CSP is unchanged."""
    data = container.ukraine_image(image_id)
    if data is None:
        raise NotFound()
    await validate_request_session(container, claims)
    return RawResponse(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
