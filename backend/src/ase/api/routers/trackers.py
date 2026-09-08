"""Tracker boards and details: hazards and curated conflicts, computed from the live store."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.routers.conflict_coverage import router as coverage_router
from ase.api.schemas_aviation import AviationBoardOut, JamCellOut, JamMapOut
from ase.api.schemas_modules import CyberBoardOut, MaritimeBoardOut, SpaceBoardOut
from ase.api.schemas_trackers import (
    ConflictBoardOut,
    ConflictCardOut,
    ConflictDetailOut,
    HazardBoardOut,
    HazardCardOut,
    HazardDetailOut,
)
from ase.application.trackers.aviation import board_with_baselines
from ase.domain.trackers import Hazard

router = APIRouter(prefix="/trackers", tags=["trackers"])
router.include_router(coverage_router)


@router.get("/disasters")
async def disaster_board(user: CurrentUser, container: ContainerDep) -> HazardBoardOut:
    cards = container.trackers().disaster_board()
    return HazardBoardOut(items=[HazardCardOut.from_card(card) for card in cards])


@router.get("/disasters/{hazard}")
async def disaster_detail(
    hazard: Hazard, user: CurrentUser, container: ContainerDep
) -> HazardDetailOut:
    return HazardDetailOut.from_detail(container.trackers().disaster_detail(hazard))


@router.get("/aviation")
async def aviation_board(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> AviationBoardOut:
    board = await board_with_baselines(
        container.aviation(), container.repositories(session).baselines
    )
    return AviationBoardOut.from_board(board)


@router.get("/aviation/jamming")
async def jamming(user: CurrentUser, container: ContainerDep) -> JamMapOut:
    service = container.aviation()
    return JamMapOut(
        cells=[JamCellOut.from_cell(cell) for cell in service.jam_cells()],
        updated_at=container.jam.updated_at,
    )


@router.get("/maritime")
async def maritime_board(user: CurrentUser, container: ContainerDep) -> MaritimeBoardOut:
    return MaritimeBoardOut.from_board(container.modules().maritime_board())


@router.get("/space")
async def space_board(user: CurrentUser, container: ContainerDep) -> SpaceBoardOut:
    return SpaceBoardOut.from_board(container.modules().space_board())


@router.get("/cyber")
async def cyber_board(user: CurrentUser, container: ContainerDep) -> CyberBoardOut:
    return CyberBoardOut.from_board(container.modules().cyber_board())


@router.get("/conflicts")
async def conflict_board(user: CurrentUser, container: ContainerDep) -> ConflictBoardOut:
    cards = container.trackers().conflict_board()
    return ConflictBoardOut(items=[ConflictCardOut.from_card(card) for card in cards])


@router.get("/conflicts/{conflict_id}")
async def conflict_detail(
    conflict_id: str, user: CurrentUser, container: ContainerDep
) -> ConflictDetailOut:
    return ConflictDetailOut.from_detail(container.trackers().conflict_detail(conflict_id))
