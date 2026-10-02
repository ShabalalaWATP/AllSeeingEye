"""Session-bound per-device opt-in, with no endpoint or auth credential in responses."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep
from ase.api.session_fence import FenceDep
from ase.container.web_push import push_sender, web_push_service
from ase.domain.web_push import PushSubscription

router = APIRouter(tags=["notifications"])


class PushSubscriptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(min_length=10, max_length=2048)
    p256dh: str = Field(min_length=87, max_length=87)
    auth: str = Field(min_length=22, max_length=22)


class PushDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    endpoint_hash: str
    created_at: datetime


class PushSettingsOut(BaseModel):
    available: bool
    public_key: str | None
    devices: list[PushDeviceOut]


@router.get("/me/notifications/push", response_model=PushSettingsOut)
async def status(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    response: Response,
) -> PushSettingsOut:
    response.headers["Cache-Control"] = "private, no-store"
    devices = await web_push_service(container, session).list(claims)
    sender = push_sender(container)
    result = PushSettingsOut(
        available=sender is not None,
        public_key=sender.public_key if sender else None,
        devices=[PushDeviceOut.model_validate(device) for device in devices],
    )
    return await fence.release(result, session=session)


@router.post("/me/notifications/push", response_model=PushDeviceOut)
async def register(
    body: PushSubscriptionIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
    response: Response,
) -> PushDeviceOut:
    response.headers["Cache-Control"] = "private, no-store"
    device = await web_push_service(container, session).register(
        claims,
        PushSubscription(
            body.endpoint,
            body.p256dh,
            body.auth,
        ),
    )
    return await fence.release(PushDeviceOut.model_validate(device), session=session)


@router.delete("/me/notifications/push/{device_id}", status_code=204)
async def remove(
    device_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    fence: FenceDep,
) -> Response:
    await web_push_service(container, session).remove(claims, device_id)
    return await fence.release(Response(status_code=204), session=session)
