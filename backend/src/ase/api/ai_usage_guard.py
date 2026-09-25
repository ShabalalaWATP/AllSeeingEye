"""Serialise allowance administration with atomic AI workspace edits."""

from typing import Annotated

from fastapi import Depends

from ase.api.deps import AdminUser, ContainerDep, SessionDep
from ase.api.session_fence import FenceDep
from ase.application.policy import require_admin
from ase.domain.users import User


async def guard_ai_usage_mutation(
    admin: AdminUser, fence: FenceDep, container: ContainerDep, session: SessionDep
) -> User:
    access = await container.access_policy(session).context(admin, for_update=True)
    require_admin(access.actor)
    await fence.confirm(session=session, admin_only=True)
    return access.actor


AiUsageMutationAdmin = Annotated[User, Depends(guard_ai_usage_mutation)]
