"""Current-account daily digest preferences, guarded like other external exports."""

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.session_fence import FenceDep
from ase.container.notifications import digest_preferences
from ase.domain.notification_digest import DigestPreferences

router = APIRouter(tags=["notifications"])


class DigestPreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    enabled: bool = False
    timezone: str = Field(default="UTC", min_length=1, max_length=100)
    hour: int = Field(default=8, ge=0, le=23)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        DigestPreferences(timezone=value)
        return value


@router.get("/me/notifications/digest", response_model=DigestPreferencesIn)
async def get_digest(
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> DigestPreferencesIn:
    response.headers["Cache-Control"] = "private, no-store"
    preferences = await digest_preferences(container, session).get(actor)
    return await fence.release(DigestPreferencesIn.model_validate(preferences), session=session)


@router.put("/me/notifications/digest", status_code=204)
async def save_digest(
    body: DigestPreferencesIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    await digest_preferences(container, session).save(
        actor,
        DigestPreferences(
            body.enabled,
            body.timezone,
            body.hour,
        ),
    )
    return await fence.release(Response(status_code=204), session=session)
