"""Name and recurrence edits retain the subscription's pinned brief and editions."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_schedules import ScheduleOut
from ase.api.schemas_subscription_settings import BriefSubscriptionSettingsIn
from ase.api.session_fence import FenceDep
from ase.api.subscription_projection import schedule_outputs
from ase.container.subscription_settings import brief_settings_editor

router = APIRouter(tags=["schedules"])


@router.put("/{schedule_id}/brief-settings")
async def edit_brief_subscription_settings(
    schedule_id: UUID,
    body: BriefSubscriptionSettingsIn,
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ScheduleOut:
    await fence.confirm(session=session)
    updated = await brief_settings_editor(container, session).execute(
        user,
        schedule_id,
        body.to_input(),
        context,
        check_session=lambda: fence.confirm(session=session),
    )
    result = (await schedule_outputs(container, session, user, [updated]))[0]
    await fence.confirm(session=session)
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result
