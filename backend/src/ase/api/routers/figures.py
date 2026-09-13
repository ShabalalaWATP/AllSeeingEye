"""Authenticated public figures board computed from the live store and the packaged roster."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_figures import FigureBoardOut
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/figures", tags=["trackers"])


@router.get("")
async def figures_board(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> FigureBoardOut:
    board = FigureBoardOut.from_board(container.public_figures().board())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return board
