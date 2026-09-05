"""Tracker boards and details: hazards and curated conflicts, computed from the live store."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_trackers import (
    ConflictBoardOut,
    ConflictCardOut,
    ConflictDetailOut,
    HazardBoardOut,
    HazardCardOut,
    HazardDetailOut,
)
from ase.domain.trackers import Hazard

router = APIRouter(prefix="/trackers", tags=["trackers"])


@router.get("/disasters")
async def disaster_board(user: CurrentUser, container: ContainerDep) -> HazardBoardOut:
    cards = container.trackers().disaster_board()
    return HazardBoardOut(items=[HazardCardOut.from_card(card) for card in cards])


@router.get("/disasters/{hazard}")
async def disaster_detail(
    hazard: Hazard, user: CurrentUser, container: ContainerDep
) -> HazardDetailOut:
    return HazardDetailOut.from_detail(container.trackers().disaster_detail(hazard))


@router.get("/conflicts")
async def conflict_board(user: CurrentUser, container: ContainerDep) -> ConflictBoardOut:
    cards = container.trackers().conflict_board()
    return ConflictBoardOut(items=[ConflictCardOut.from_card(card) for card in cards])


@router.get("/conflicts/{conflict_id}")
async def conflict_detail(
    conflict_id: str, user: CurrentUser, container: ContainerDep
) -> ConflictDetailOut:
    return ConflictDetailOut.from_detail(container.trackers().conflict_detail(conflict_id))
