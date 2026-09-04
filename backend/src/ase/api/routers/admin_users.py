"""User administration (admin only)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas import ResetLinkOut, UpdateUserIn, UserOut, UsersOut

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("")
async def list_users(admin: AdminUser, session: SessionDep, container: ContainerDep) -> UsersOut:
    users = await container.list_users(session).execute(admin)
    return UsersOut(items=[UserOut.from_user(user) for user in users])


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    body: UpdateUserIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> UserOut:
    user = await container.update_user(session).execute(
        admin, user_id, body.role, body.is_active, context
    )
    return UserOut.from_user(user)


@router.post("/{user_id}/reset-link")
async def issue_reset_link(
    user_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> ResetLinkOut:
    result = await container.issue_reset_link(session).execute(admin, user_id, context)
    return ResetLinkOut(reset_link=result.reset_link, expires_at=result.expires_at)
