"""MFA-protected enquiry review with a release fence on every response."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import AdminUser, ClaimsDep, ContainerDep, SessionDep
from ase.api.schemas_enquiries import EnquiriesOut, EnquiryOut, EnquiryStatusIn
from ase.api.session_fence import FenceDep
from ase.domain.enterprise_enquiries import EnquiryStatus

router = APIRouter(prefix="/admin/enquiries", tags=["admin"])


@router.get("")
async def list_enquiries(
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    fence: FenceDep,
    enquiry_status: Annotated[EnquiryStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EnquiriesOut:
    items, total = await container.admin_enquiries(session).list(
        admin, enquiry_status, limit, offset
    )
    result = EnquiriesOut(items=[EnquiryOut.from_entity(item) for item in items], total=total)
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(result, session=session, admin_only=True)


@router.get("/{enquiry_id}")
async def get_enquiry(
    enquiry_id: UUID,
    admin: AdminUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    fence: FenceDep,
) -> EnquiryOut:
    result = EnquiryOut.from_entity(await container.admin_enquiries(session).get(admin, enquiry_id))
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(result, session=session, admin_only=True)


@router.patch("/{enquiry_id}")
async def update_enquiry(
    enquiry_id: UUID,
    body: EnquiryStatusIn,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    fence: FenceDep,
) -> EnquiryOut:
    result = EnquiryOut.from_entity(
        await container.admin_enquiries(session).set_status(claims, enquiry_id, body.status)
    )
    response.headers["Cache-Control"] = "no-store"
    return await fence.release(result, session=session, admin_only=True)


@router.delete("/{enquiry_id}", status_code=204)
async def delete_enquiry(
    enquiry_id: UUID,
    admin: AdminUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    await container.admin_enquiries(session).delete(claims, enquiry_id)
    result = Response(status_code=204, headers={"Cache-Control": "no-store"})
    return await fence.release(result, session=session, admin_only=True)
