"""The signed-in user."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import CurrentUser
from ase.api.schemas import UserOut

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.from_user(user)
