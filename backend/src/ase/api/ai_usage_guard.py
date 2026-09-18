"""Serialise allowance administration with atomic AI workspace edits."""

from typing import Annotated

from fastapi import Depends

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, SessionDep
from ase.api.session_guard import validate_request_session
from ase.application.policy import require_admin
from ase.domain.users import User


async def guard_ai_usage_mutation(
    admin: AdminUser, claims: ClaimsDep, container: ContainerDep, session: SessionDep
) -> User:
    access = await container.access_policy(session).context(admin, for_update=True)
    require_admin(access.actor)
    await validate_request_session(container, claims, session=session, admin_only=True)
    return access.actor


AiUsageMutationAdmin = Annotated[User, Depends(guard_ai_usage_mutation)]
