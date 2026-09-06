"""Warning configuration and alert visibility are bounded by current team membership."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.warning_mapping import _alert_row
from ase.application.direction.plans import PirInput, PlanInput
from ase.container import Container
from ase.domain.users import User
from ase.domain.warning import Alert
from helpers import USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import WarningActors, create_indicator
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


@pytest.mark.parametrize("resource", ["/warning/indicators", "/schedules"])
async def test_scope_lists_and_current_team_write_permissions(
    client: AsyncClient,
    container: Container,
    admin: User,
    warning_actors: WarningActors,
    resource: str,
) -> None:
    actors = warning_actors
    tokens = {
        actor.id: await login_token(client, actor.email, USER_PASSWORD)
        for actor in (actors.owner, actors.peer, actors.manager, actors.outsider)
    }
    body = {"name": "Team product", "team_id": str(actors.team.id)}
    if resource == "/schedules":
        body["template_id"] = "intsum"
    created = await client.post(
        f"/api{resource}", json=body, headers=bearer(tokens[actors.owner.id])
    )
    assert created.status_code == 201, created.text
    identity = created.json()["id"]
    foreign = await client.post(
        f"/api{resource}",
        json={**body, "team_id": str(actors.other.id)},
        headers=bearer(tokens[actors.outsider.id]),
    )
    assert foreign.status_code == 201
    # A global manager who is only a member of this other team cannot edit its owner's record.
    assert (
        await client.put(
            f"/api{resource}/{foreign.json()['id']}",
            json={**body, "team_id": str(actors.other.id)},
            headers=bearer(tokens[actors.manager.id]),
        )
    ).status_code == 403
    assert (
        await client.post(
            f"/api{resource}",
            json={**body, "team_id": str(actors.other.id)},
            headers=bearer(tokens[actors.peer.id]),
        )
    ).status_code == 404
    personal = await client.post(
        f"/api{resource}", json={**body, "team_id": None}, headers=bearer(tokens[actors.owner.id])
    )
    assert personal.status_code == 201
    peer_list = await client.get(f"/api{resource}", headers=bearer(tokens[actors.peer.id]))
    assert [item["id"] for item in peer_list.json()["items"]] == [identity]
    outsider_list = await client.get(f"/api{resource}", headers=bearer(tokens[actors.outsider.id]))
    assert [item["id"] for item in outsider_list.json()["items"]] == [foreign.json()["id"]]
    for actor, status in ((actors.peer, 403), (actors.outsider, 404), (actors.manager, 200)):
        changed = await client.put(
            f"/api{resource}/{identity}", json=body, headers=bearer(tokens[actor.id])
        )
        assert changed.status_code == status, changed.text
    assert (
        await client.put(
            f"/api{resource}/{identity}",
            json={**body, "team_id": None},
            headers=bearer(tokens[actors.owner.id]),
        )
    ).status_code == 422
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    assert (
        await client.put(
            f"/api{resource}/{identity}", json=body, headers=bearer(tokens[actors.owner.id])
        )
    ).status_code == 404
    remaining = await client.get(f"/api{resource}", headers=bearer(tokens[actors.owner.id]))
    assert [item["id"] for item in remaining.json()["items"]] == [personal.json()["id"]]
    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=False, context=CONTEXT)
    archived = await client.put(
        f"/api{resource}/{identity}", json=body, headers=bearer(tokens[actors.manager.id])
    )
    assert archived.status_code == 403
    assert (
        len(
            (await client.get(f"/api{resource}", headers=bearer(tokens[actors.peer.id]))).json()[
                "items"
            ]
        )
        == 1
    )


@pytest.mark.parametrize("resource", ["/warning/indicators", "/schedules"])
async def test_linked_plan_must_share_exact_scope(
    client: AsyncClient,
    container: Container,
    warning_actors: WarningActors,
    resource: str,
) -> None:
    actors = warning_actors
    async with container.session_factory() as session:
        personal = await container.create_plan(session).execute(
            actors.owner,
            PlanInput("Private plan", pirs=(PirInput("What changed?"),)),
            CONTEXT,
        )
        team = await container.create_plan(session).execute(
            actors.peer,
            PlanInput("Team plan", pirs=(PirInput("What changed?"),), team_id=actors.team.id),
            CONTEXT,
        )
    token = await login_token(client, actors.owner.email, USER_PASSWORD)
    body = {"name": "Scoped product", "team_id": str(actors.team.id)}
    if resource == "/schedules":
        body["template_id"] = "intsum"
    mismatch = await client.post(
        f"/api{resource}", headers=bearer(token), json={**body, "plan_id": str(personal.id)}
    )
    assert mismatch.status_code == 422
    valid = await client.post(
        f"/api{resource}", headers=bearer(token), json={**body, "plan_id": str(team.id)}
    )
    assert valid.status_code == 201, valid.text


async def test_alerts_filter_before_limit_and_keep_scope_after_indicator_deletion(
    client: AsyncClient,
    container: Container,
    admin: User,
    warning_actors: WarningActors,
) -> None:
    actors = warning_actors
    rule = await create_indicator(container, actors.owner, actors.team.id)
    visible = Alert(
        uuid4(),
        rule.id,
        container.clock.now() - timedelta(hours=1),
        "Visible older alert",
        "",
        1,
        1,
        (),
        (),
        created_by=actors.owner.id,
        team_id=actors.team.id,
    )
    hidden = replace(
        visible,
        id=uuid4(),
        fired_at=container.clock.now(),
        created_by=actors.outsider.id,
        team_id=actors.other.id,
        title="Private newer alert",
    )
    orphan = replace(hidden, id=uuid4(), created_by=None, team_id=None, title="Legacy orphan")
    async with container.session_factory() as session:
        session.add_all([_alert_row(item) for item in (visible, hidden, orphan)])
        await session.commit()
    token = await login_token(client, actors.peer.email, USER_PASSWORD)
    found = await client.get("/api/warning/alerts?limit=1", headers=bearer(token))
    assert found.json()["items"][0]["id"] == str(visible.id)
    assert found.json()["unacknowledged"] == 1
    assert (
        await client.post(f"/api/warning/alerts/{visible.id}/ack", headers=bearer(token))
    ).status_code == 200
    assert (
        await client.post(f"/api/warning/alerts/{hidden.id}/ack", headers=bearer(token))
    ).status_code == 404
    async with container.session_factory() as session:
        await container.delete_indicator(session).execute(actors.owner, rule.id, CONTEXT)
    manager = await login_token(client, actors.manager.email, USER_PASSWORD)
    ack = await client.post(f"/api/warning/alerts/{visible.id}/ack", headers=bearer(manager))
    assert ack.status_code == 200 and ack.json()["created_by"] == str(actors.owner.id)
    assert ack.json()["team_id"] == str(actors.team.id)
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.peer.id, CONTEXT)
    assert (await client.get("/api/warning/alerts", headers=bearer(token))).json()["items"] == []
