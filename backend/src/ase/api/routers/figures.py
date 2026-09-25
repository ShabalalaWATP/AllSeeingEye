"""Authenticated public figures board computed from the live store and the packaged roster."""

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_figures import FigureBoardOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/figures", tags=["trackers"])


@router.get("")
async def figures_board(
    user: CurrentUser,
    response: Response,
    container: ContainerDep,
    fence: FenceDep,
) -> FigureBoardOut:
    board = FigureBoardOut.from_board(container.public_figures().board())
    await fence.confirm()
    response.headers["Cache-Control"] = "private, no-store"
    return board
