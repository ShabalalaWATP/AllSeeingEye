"""Computed social listening board, with collection terms restricted to their owner."""

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_social import SocialBoardOut

router = APIRouter(prefix="/trackers/social", tags=["trackers"])


@router.get("")
async def social_board(user: CurrentUser, container: ContainerDep) -> SocialBoardOut:
    return SocialBoardOut.from_board(await container.social().board(user))
