"""Authenticated Ukraine war tracker: the board from the live store, control from the snapshot."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_ukraine import ControlOut, UkraineBoardOut
from ase.api.session_guard import validate_request_session

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
