"""Identity changes cannot expose another person's photo or release revoked team work."""

from dataclasses import replace

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from helpers import USER_PASSWORD, create_user
from photo_helpers import Vision, profile, session_check, upload
from team_helpers import CONTEXT, team_service


async def test_other_active_user_cannot_use_private_receipt(
    container: Container,
    user: User,
) -> None:
    await profile(container)
    other = await create_user(
        container, email="other-photo@example.invalid", password=USER_PASSWORD
    )
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.photo_geolocation(session).execute(
                other,
                input_id,
                consent_to_send_image=True,
                check_session=session_check,
            )
    assert not vision.calls


async def test_team_membership_removal_during_vision_prevents_retention(
    container: Container,
    user: User,
    admin: User,
) -> None:
    await profile(container)
    async with team_service(container) as teams:
        team = await teams.create(admin, "Photo team", CONTEXT)
        await teams.set_member(
            admin,
            team.id,
            email=user.email,
            role=MembershipRole.MEMBER,
            context=CONTEXT,
        )
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision

    async def revoke() -> None:
        async with team_service(container) as teams:
            await teams.remove_member(admin, team.id, user.id, CONTEXT)

    vision.after = revoke
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.photo_geolocation(session).execute(
                user,
                input_id,
                consent_to_send_image=True,
                team_id=team.id,
                check_session=session_check,
            )
    assert len(vision.calls) == 1
    assert len(container.research_inputs._ready) == 1


@pytest.mark.parametrize("invalid", ["text", "derived", "digest", "question", "hints"])
async def test_invalid_photo_requests_do_not_reach_vision(
    invalid: str,
    container: Container,
    user: User,
) -> None:
    await profile(container)
    input_id = upload(container, user)
    store = container.research_inputs
    original = store._ready[input_id]
    if invalid == "text":
        store._ready[input_id] = replace(
            original, receipt=replace(original.receipt, media_type="text/plain")
        )
    elif invalid == "derived":
        store._ready[input_id] = replace(
            original, receipt=replace(original.receipt, parent_input_id=input_id)
        )
    elif invalid == "digest":
        store._ready[input_id] = replace(
            original, frames=(replace(original.frames[0], sha256="0" * 64),)
        )
    vision = Vision()
    container.llm = vision
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest):
            await container.photo_geolocation(session).execute(
                user,
                input_id,
                consent_to_send_image=True,
                check_session=session_check,
                question="x" * 2001 if invalid == "question" else "Where?",
                hints="x" * 1001 if invalid == "hints" else "",
            )
    assert not vision.calls


async def test_failed_calls_are_rate_limited_without_consuming_private_slots(
    container: Container,
    user: User,
) -> None:
    await profile(container)
    input_id = upload(container, user)
    vision = Vision()
    vision.error = LlmGatewayError("Vision unsupported")
    container.llm = vision
    async with container.session_factory() as session:
        service = container.photo_geolocation(session)
        for _ in range(2):
            with pytest.raises(InvalidRequest):
                await service.execute(
                    user, input_id, consent_to_send_image=True, check_session=session_check
                )
        with pytest.raises(RateLimited):
            await service.execute(
                user, input_id, consent_to_send_image=True, check_session=session_check
            )
    assert len(vision.calls) == 2 and len(container.research_inputs._reservations) == 1
