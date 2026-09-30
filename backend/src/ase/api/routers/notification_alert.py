"""An opaque notification ID is resolved only through the authenticated alert boundary."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_warning import AlertOut
from ase.api.session_fence import FenceDep

router = APIRouter(tags=["notifications"])


@router.get("/warning/alerts/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: UUID,
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    response: Response,
) -> AlertOut:
    response.headers["Cache-Control"] = "private, no-store"
    alert = await container.list_alerts(session).get(actor, alert_id)
    return await fence.release(AlertOut.from_alert(alert), session=session)
