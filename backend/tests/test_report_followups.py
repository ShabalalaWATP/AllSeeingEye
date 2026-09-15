"""Bounded parent evidence reuse with current read access and immutable version links."""

from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from report_input_helpers import (
    CallbackGateway,
    actor_headers,
    model_setup,
    report_payload,
    saved_parent,
)
from team_helpers import CONTEXT, team_service


async def member_team(container: Container, admin: User, user: User):
    async with team_service(container) as service:
        team = await service.create(admin, "Follow-up desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        return team


async def test_team_member_can_follow_up_parent_they_cannot_modify(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    team = await member_team(container, admin, user)
    parent, original = await saved_parent(container, admin, team.id)
    collection = await model_setup(client, container, admin)
    headers = await actor_headers(client, user)
    assert (await client.delete(f"/api/reports/{parent.id}", headers=headers)).status_code == 403
    gateway = CallbackGateway()
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id), team_id=str(team.id)),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["report"]["id"] != str(parent.id)
    assert payload["report"]["created_by"] == str(user.id)
    assert payload["version"]["number"] == 1
    assert payload["report"]["scope"]["parent_report_id"] == str(parent.id)
    assert payload["report"]["scope"]["parent_version"] == 1
    assert len(payload["version"]["evidence"]) == len(original.evidence)
    source = original.evidence[0]
    frozen = payload["version"]["evidence"][0]
    assert frozen["event_id"] == source.event_id
    assert frozen["grade"] == source.grade
    assert frozen["source_name"] == source.source_name
    assert frozen["published_at"].startswith(source.published_at.date().isoformat())
    assert frozen["archive_url"] == source.archive_url
    assert original.body.key_judgements[0].statement in " ".join(
        message.content for message in gateway.requests[1].messages
    )
    assert collection.calls == 0
    assert all(container.store.get(item.event_id) is None for item in original.evidence)
    async with container.session_factory() as session:
        current = await container.repositories(session).reports.get(parent.id)
        assert current is not None and current.latest_version == 1


@pytest.mark.parametrize("case", ["foreign_personal", "personal_to_team", "team_to_personal"])
async def test_follow_up_cannot_cross_personal_or_team_scope(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
    case: str,
) -> None:
    team = await member_team(container, admin, user)
    owner = admin if case == "foreign_personal" else user
    parent, _ = await saved_parent(
        container, owner, team.id if case == "team_to_personal" else None
    )
    await model_setup(client, container, admin)
    gateway = CallbackGateway()
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json=report_payload(
            parent_report_id=str(parent.id),
            team_id=str(team.id) if case == "personal_to_team" else None,
        ),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == (404 if case == "foreign_personal" else 422)
    assert "Frozen report source detail" not in response.text
    assert gateway.requests == []


async def test_private_parent_cannot_silently_become_public_research(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    parent, _ = await saved_parent(container, user)
    collection = await model_setup(client, container, admin)
    gateway = CallbackGateway()
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id), research_focus="general"),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 422
    assert "Private-source follow-ups" in response.text
    assert collection.calls == 0 and gateway.requests == []


async def test_follow_up_rechecks_membership_after_model_work(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    team = await member_team(container, admin, user)
    parent, _ = await saved_parent(container, admin, team.id)
    await model_setup(client, container, admin)

    async def revoke() -> None:
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)

    container.llm = CallbackGateway(revoke)
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id), team_id=str(team.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 404, response.text
    assert "Frozen report source detail" not in response.text
    async with container.session_factory() as session:
        repos = container.repositories(session)
        records = await repos.reports.list_recent(20)
        assert [record.id for record in records] == [parent.id]
        assert await repos.llm_usage.list_recent(20) == []


async def test_deleted_parent_blocks_new_report_even_if_destination_still_authorised(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    parent, _ = await saved_parent(container, user)
    await model_setup(client, container, admin)

    async def delete_parent() -> None:
        async with container.session_factory() as session:
            await container.delete_report(session).execute(user, parent.id, CONTEXT)

    container.llm = CallbackGateway(delete_parent)
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 404, response.text
    async with container.session_factory() as session:
        repos = container.repositories(session)
        assert await repos.reports.list_recent(20) == []
        assert await repos.llm_usage.list_recent(20) == []


async def test_new_parent_version_does_not_replace_bound_context(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    parent, original = await saved_parent(container, user)
    await model_setup(client, container, admin)

    async def add_later_version() -> None:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            current = await repos.reports.get(parent.id)
            assert current is not None
            current.latest_version = 2
            later = replace(original, id=uuid4(), number=2, evidence=())
            await repos.reports.add_version(current, later)
            await session.commit()

    container.llm = CallbackGateway(add_later_version)
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id)),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["version"]["number"] == 1
    assert payload["report"]["scope"]["parent_version"] == 1
    assert len(payload["version"]["evidence"]) == len(original.evidence)
    async with container.session_factory() as session:
        current = await container.repositories(session).reports.get(parent.id)
        assert current is not None and current.latest_version == 2


async def test_selected_older_parent_version_remains_the_followup_source(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    parent, original = await saved_parent(container, user)
    await model_setup(client, container, admin)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.reports.get(parent.id)
        assert current is not None
        current.latest_version = 2
        later = replace(original, id=uuid4(), number=2, evidence=())
        await repos.reports.add_version(current, later)
        await session.commit()
    container.llm = CallbackGateway()
    response = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id), parent_version=1),
        headers=await actor_headers(client, user),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["report"]["scope"]["parent_version"] == 1
    assert len(payload["version"]["evidence"]) == len(original.evidence)


async def test_admin_can_regenerate_same_owner_personal_follow_up(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    parent, _ = await saved_parent(container, user)
    await model_setup(client, container, admin)
    created = await client.post(
        "/api/reports",
        json=report_payload(parent_report_id=str(parent.id)),
        headers=await actor_headers(client, user),
    )
    assert created.status_code == 201, created.text
    container.llm = CallbackGateway()
    response = await client.post(
        f"/api/reports/{created.json()['report']['id']}/versions",
        headers=await actor_headers(client, admin, admin=True),
    )
    assert response.status_code == 201, response.text
    assert response.json()["version"]["number"] == 2
