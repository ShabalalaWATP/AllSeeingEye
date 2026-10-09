"""Unauthenticated, opt-in enquiries: no account or private record is returned."""

from fastapi import APIRouter, Depends, Response

from ase.api.deps import ContainerDep, ContextDep, SessionDep
from ase.api.schemas import MessageOut
from ase.api.schemas_enquiries import EnquiryIn
from ase.domain.errors import NotFound

router = APIRouter(tags=["enquiries"])


def require_enabled(container: ContainerDep) -> None:
    if not container.settings.enterprise_enquiries_enabled:
        raise NotFound()


@router.post("/enquiries", status_code=202, dependencies=[Depends(require_enabled)])
async def submit_enquiry(
    body: EnquiryIn,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> MessageOut:
    response.headers["Cache-Control"] = "no-store"
    await container.submit_enquiry(session).execute(
        body.details(), context.client_key, honeypot=body.website
    )
    return MessageOut(message="Thank you. Your enquiry has been received.")
