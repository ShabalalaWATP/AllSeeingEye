"""Account request review (admin only)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from ase.api.deps import AdminUser, ContainerDep, ContextDep, SessionDep
from ase.api.schemas import (
    AccountRequestOut,
    AccountRequestsOut,
    ApproveIn,
    ApproveOut,
    RejectIn,
    UserOut,
)
from ase.api.session_fence import FenceDep
from ase.domain.users import RequestStatus

router = APIRouter(prefix="/admin/account-requests", tags=["admin"])


@router.get("")
async def list_requests(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    request_status: Annotated[RequestStatus, Query(alias="status")] = RequestStatus.PENDING,
) -> AccountRequestsOut:
    items = await container.list_requests(session).execute(admin, request_status)
    return AccountRequestsOut(items=[AccountRequestOut.from_entity(item) for item in items])


@router.post("/{request_id}/approve")
async def approve_request(
    request_id: UUID,
    body: ApproveIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    fence: FenceDep,
) -> ApproveOut:
    result = await container.approve_request(session).execute(admin, request_id, body.role, context)
    # Approval is already committed; email delivery must not let a revoked caller receive a key.
    await fence.confirm(admin_only=True)
    return ApproveOut(
        user=UserOut.from_user(result.user),
        activation_link=result.activation_link,
        expires_at=result.expires_at,
    )


@router.post("/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_request(
    request_id: UUID,
    body: RejectIn,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.reject_request(session).execute(admin, request_id, body.reason, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
