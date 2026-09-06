"""Private upload use, capability expiry, frozen regeneration and safe metadata."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.errors import NotFound
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import FakeClock
from report_input_helpers import (
    CallbackGateway,
    actor_headers,
    model_setup,
    report_payload,
    stored_input,
)


@pytest.mark.parametrize("focus", ["document", "media"])
async def test_uploaded_content_is_private_and_capability_id_is_not_persisted(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    focus: str,
) -> None:
    collection = await model_setup(client, container, admin)
    stored = stored_input(container, user)
    unrelated = make_event(
        "unrelated-live",
        title="Unrelated retained live reporting",
        published_at=container.clock.now() - timedelta(hours=1),
        observed_at=container.clock.now(),
    )
    container.store.upsert([unrelated])
    response = await client.post(
        "/api/reports",
        json=report_payload(research_focus=focus, research_input_id=str(stored.receipt.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert len(payload["version"]["evidence"]) == 3
    assert collection.calls == 0
    assert all(container.store.get(item.id) is None for item in stored.events)
    assert container.store.get(unrelated.id) == unrelated
    assert str(stored.receipt.id) not in response.text
    metadata = payload["report"]["scope"]["research_input"]
    assert metadata["sha256"] == stored.receipt.sha256
    assert metadata["filename"] == "private-brief.txt"
    assert "preview" not in metadata
    receipt = payload["version"]["research"]
    assert receipt["collected_items"] == 0
    assert receipt["attempts"][0]["source_id"] == "research-upload"
    assert receipt["attempts"][0]["result_count"] == 3
    saved = await client.get(
        f"/api/reports/{payload['report']['id']}", headers=await actor_headers(client, user)
    )
    assert saved.status_code == 200
    assert str(stored.receipt.id) not in saved.text
    assert saved.json()["version"]["evidence"] == payload["version"]["evidence"]


@pytest.mark.parametrize("focus", ["document", "media"])
async def test_private_focus_without_input_fails_before_model_or_collection(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    focus: str,
) -> None:
    collection = await model_setup(client, container, admin)
    gateway = CallbackGateway()
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json=report_payload(research_focus=focus),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 422
    assert "requires a private input" in response.text
    assert gateway.requests == [] and collection.calls == 0


async def test_input_token_is_owner_bound_even_for_administrators(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    collection = await model_setup(client, container, admin)
    stored = stored_input(container, user)
    response = await client.post(
        "/api/reports",
        json=report_payload(research_input_id=str(stored.receipt.id)),
        headers=await actor_headers(client, admin, admin=True),
    )
    assert response.status_code == 404
    assert "Private extracted" not in response.text
    assert collection.calls == 0


async def test_expired_input_cannot_start_generation(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    clock: FakeClock,
) -> None:
    await model_setup(client, container, admin)
    stored = stored_input(container, user)
    clock.advance(timedelta(minutes=16))
    response = await client.post(
        "/api/reports",
        json=report_payload(research_input_id=str(stored.receipt.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 404


async def test_input_from_old_security_version_cannot_be_used_after_reauthentication(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    await model_setup(client, container, admin)
    stored = stored_input(container, user)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.get_by_id(user.id)
        assert current is not None
        current.security_version += 1
        await repos.users.save(current)
        await session.commit()
    response = await client.post(
        "/api/reports",
        json=report_payload(research_input_id=str(stored.receipt.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("mode", [None, "quick"])
async def test_upload_cannot_implicitly_enable_public_querying(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    mode: str | None,
) -> None:
    collection = await model_setup(client, container, admin)
    stored = stored_input(container, user)
    response = await client.post(
        "/api/reports",
        json=report_payload(
            research_mode=mode, research_focus="general", research_input_id=str(stored.receipt.id)
        ),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 422
    assert collection.calls == 0


async def test_regeneration_reuses_frozen_evidence_after_input_expiry_and_window(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    clock: FakeClock,
) -> None:
    collection = await model_setup(client, container, admin)
    stored = stored_input(container, user)
    response = await client.post(
        "/api/reports",
        json=report_payload(research_input_id=str(stored.receipt.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 201, response.text
    first = response.json()
    clock.advance(timedelta(days=16))
    with pytest.raises(NotFound):
        container.research_inputs.read(user, stored.receipt.id)
    container.llm = CallbackGateway()
    response = await client.post(
        f"/api/reports/{first['report']['id']}/versions", headers=await actor_headers(client, user)
    )
    assert response.status_code == 201, response.text
    second = response.json()
    assert second["version"]["number"] == 2
    assert second["version"]["evidence"] == first["version"]["evidence"]
    assert str(stored.receipt.id) not in response.text
    assert collection.calls == 0
    receipt = second["version"]["research"]
    assert receipt["collected_items"] == 0
    assert receipt["attempts"][0]["source_id"] == "research-reused-evidence"
    assert "version 1" in receipt["attempts"][0]["explanation"]
    assert all(container.store.get(item.id) is None for item in stored.events)
