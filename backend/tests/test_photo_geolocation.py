"""Private vision analysis preserves ownership, destination routing and uncertain evidence."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.application.ports.llm import LlmGatewayError
from ase.container import Container
from ase.domain.errors import (
    InvalidRequest,
    NoModelAvailable,
    NotFound,
    RateLimited,
    Unauthenticated,
)
from ase.domain.llm import TEXT_ROLES, LlmConnectionBinding
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from photo_helpers import Vision, profile, session_check, upload


async def test_http_unknown_uses_real_image_and_retains_only_derived_text(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    chosen = await profile(container)
    input_id = upload(container, user)
    original = container.research_inputs.read(user, input_id)
    vision = Vision()
    container.llm = vision
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        f"/api/research/inputs/{input_id}/geolocation",
        headers=bearer(token),
        json={"consent_to_send_image": True, "hints": "Unverified: London"},
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert response.headers["cache-control"] == "private, no-store"
    assert result["status"] == "unknown" and result["candidates"] == []
    assert result["candidate_status"] == "unverified"
    assert result["provenance"]["profile_id"] == str(chosen.id)
    assert result["provenance"]["returned_model"] == "returned-vision-fixture"
    assert "png_base64" not in response.text and "private-fixture-key" not in response.text
    sent = vision.calls[0][3]
    assert sent.messages[1].images[0].png == original.frames[0].png
    assert b"Private EXIF" not in sent.messages[1].images[0].png
    assert "data:image" not in sent.messages[1].content
    assert "Unverified: London" in sent.messages[1].content
    assert sent.reasoning_effort == chosen.reasoning_effort
    derived = container.research_inputs.read(user, UUID(result["input"]["id"]))
    assert derived.receipt.parent_input_id == input_id and not derived.frames
    assert derived.receipt.expires_at == original.receipt.expires_at
    assert all(event.point is None and event.published_at is None for event in derived.events)
    assert all("UNVERIFIED" in event.summary for event in derived.events)
    async with container.session_factory() as session:
        usages = await container.repositories(session).llm_usage.list_recent(10)
    assert len(usages) == 1 and usages[0].ok and usages[0].prompt_tokens == 400


@pytest.mark.parametrize("case", ["consent", "owner", "team", "no-model"])
async def test_no_image_disclosure_without_preconditions(
    case: str,
    container: Container,
    user: User,
) -> None:
    input_id = upload(container, user)
    if case != "no-model":
        await profile(container)
    vision = Vision()
    container.llm = vision
    actor = replace(user, id=uuid4()) if case == "owner" else user
    error = {
        "consent": InvalidRequest,
        "owner": Unauthenticated,
        "team": NotFound,
        "no-model": NoModelAvailable,
    }[case]
    async with container.session_factory() as session:
        with pytest.raises(error):
            await container.photo_geolocation(session).execute(
                actor,
                input_id,
                consent_to_send_image=case != "consent",
                team_id=uuid4() if case == "team" else None,
                check_session=session_check,
            )
    assert not vision.calls


@pytest.mark.parametrize(
    "change", ["expiry", "session", "account", "cancel", "invalid", "provider"]
)
async def test_failed_or_revoked_work_never_releases_derived_receipt(
    change: str,
    container: Container,
    user: User,
) -> None:
    await profile(container)
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision
    check_count = 0

    async def check() -> None:
        nonlocal check_count
        check_count += 1
        if change == "session" and check_count == 3:
            raise Unauthenticated()

    async def alter() -> None:
        if change == "expiry":
            container.clock.advance(timedelta(minutes=16))
        elif change == "account":
            async with container.session_factory() as changed:
                repo = container.repositories(changed).users
                current = await repo.get_by_id(user.id)
                current.is_active = False
                await repo.save(current)
                await changed.commit()
        elif change == "cancel":
            raise asyncio.CancelledError()

    vision.after = alter
    if change == "invalid":
        vision.content = '{"secret_input": "private fixture"}'
    if change == "provider":
        vision.error = LlmGatewayError("The configured model rejected image analysis.")
    expected = {
        "expiry": NotFound,
        "session": Unauthenticated,
        "account": Unauthenticated,
        "cancel": asyncio.CancelledError,
        "invalid": InvalidRequest,
        "provider": InvalidRequest,
    }[change]
    async with container.session_factory() as session:
        with pytest.raises(expected):
            await container.photo_geolocation(session).execute(
                user,
                input_id,
                consent_to_send_image=True,
                check_session=check,
            )
    assert not container.photo_admission.locked()
    store = container.research_inputs
    assert all(row.receipt.parent_input_id is None for row in store._ready.values())
    async with container.session_factory() as session:
        usages = await container.repositories(session).llm_usage.list_recent(10)
    assert len(usages) == 1
    assert usages[0].ok == (change in {"expiry", "session", "account"})
    assert "private fixture" not in str(usages[0])


async def test_personal_binding_wins_and_expiry_cannot_be_extended(
    container: Container,
    user: User,
) -> None:
    await profile(container, "global-fixture")
    chosen = await profile(container, "personal-fixture")
    chosen.roles = TEXT_ROLES
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.llm_profiles.save(chosen)
        await repos.llm_bindings.save(
            LlmConnectionBinding(
                None,
                chosen.id,
                chosen.revision,
                chosen.config_hash,
                container.clock.now(),
                user.id,
                user_id=user.id,
            )
        )
        await session.commit()
    input_id = upload(container, user)
    original = container.research_inputs.read(user, input_id)
    container.clock.advance(timedelta(minutes=4))
    vision = Vision()
    container.llm = vision
    async with container.session_factory() as session:
        result = await container.photo_geolocation(session).execute(
            user,
            input_id,
            consent_to_send_image=True,
            check_session=session_check,
        )
    assert vision.calls[0][2] == "personal-fixture"
    assert result.receipt.expires_at == original.receipt.expires_at


async def test_admission_is_bounded_before_network(container: Container, user: User) -> None:
    await profile(container)
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision
    await container.photo_admission.acquire()
    await container.photo_admission.acquire()
    try:
        async with container.session_factory() as session:
            with pytest.raises(RateLimited):
                await container.photo_geolocation(session).execute(
                    user,
                    input_id,
                    consent_to_send_image=True,
                    check_session=session_check,
                )
    finally:
        container.photo_admission.release()
        container.photo_admission.release()
    assert not vision.calls
