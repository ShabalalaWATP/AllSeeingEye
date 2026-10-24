"""Computed social listening board, with collection terms restricted to their owner."""

from fastapi import APIRouter

from ase.api.board_response import read_board_response
from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_social import SocialBoardOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/trackers/social", tags=["trackers"])


@router.get("")
async def social_board(
    user: CurrentUser, container: ContainerDep, fence: FenceDep
) -> SocialBoardOut:
    service = container.social()
    board = await read_board_response(
        container,
        fence,
        lambda: service.board(user, admission_key=f"user:{user.id}"),
        final_authority=lambda result: service.confirm_visible(user, result),
    )
    return SocialBoardOut.from_board(board)
