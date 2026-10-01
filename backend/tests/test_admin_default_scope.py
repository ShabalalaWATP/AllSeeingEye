"""Administrators default to their own personal and current-team work (KAN-90).

The broad administrative view remains an explicit ``scope=all`` request that only
administrators may make. Ownership filters run in SQL before limits and counts.
"""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from httpx import AsyncClient

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.container import Container
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from ase.domain.warning import Alert
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token
from report_job_helpers import NOW, job
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import WarningActors
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414

RULE = uuid4()  # every fixture alert needs exactly one origin; scope is the alert's own
USAGE = {
    "calls": 0,
    "max_calls": 40,
    "output_tokens": 0,
    "output_allowance": 1,
    "uncertain_calls": 0,
}
SUMMARY = {
    "completed_sections": 0,
    "total_sections": 0,
    "model": "fixture-model",
    "reasoning_effort": None,
    "usage": USAGE,
}


async def _join(container: Container, admin: User, actors: WarningActors) -> User:
    """The administrator belongs to the warning desk but not to the other desk.

    Team creation enrols its creator; administrators cannot change their own membership,
    so a second administrator removes the first from the other desk.
    """
    second = await create_user(
        container, email="second-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    async with team_service(container) as service:
        await service.set_member(
            second,
            actors.other.id,
            email=actors.manager.email,
            role=MembershipRole.MANAGER,
            context=CONTEXT,
        )
        await service.remove_member(second, actors.other.id, admin.id, CONTEXT)
    return second


def _alert(container: Container, title: str, minutes: int, **scope: object) -> Alert:
    base = Alert(
        uuid4(),
        RULE,
        container.clock.now() - timedelta(minutes=minutes),
        title,
        "",
        1,
        1,
        (),
        (),
    )
    return replace(base, **scope)  # type: ignore[arg-type]


async def test_admin_alerts_default_to_own_work_before_limits_and_counts(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    second = await _join(container, admin, actors)
    own = _alert(container, "Admin personal", 30, created_by=admin.id, team_id=None)
    other = actors.other.id
    team = _alert(container, "Desk alert", 20, created_by=actors.owner.id, team_id=actors.team.id)
    # Newer unrelated records must not displace the administrator's own records.
    unrelated = [
        _alert(container, f"Other personal {n}", n, created_by=actors.owner.id, team_id=None)
        for n in range(1, 6)
    ] + [
        _alert(container, f"Other desk {n}", n, created_by=actors.outsider.id, team_id=other)
        for n in range(6, 11)
    ]
    async with container.session_factory() as session:
        session.add_all([_alert_row(item) for item in (own, team, *unrelated)])
        await session.commit()
    token = await login_token(client, admin.email, ADMIN_PASSWORD)

    default = (await client.get("/api/warning/alerts?limit=2", headers=bearer(token))).json()
    assert [row["id"] for row in default["items"]] == [str(team.id), str(own.id)]
    assert default["unacknowledged"] == 2
    assert default["items"][1]["owner_name"] == admin.display_name
    mine = (await client.get("/api/warning/alerts?scope=mine", headers=bearer(token))).json()
    assert {row["id"] for row in mine["items"]} == {str(team.id), str(own.id)}

    everyone = (await client.get("/api/warning/alerts?scope=all", headers=bearer(token))).json()
    assert len(everyone["items"]) == 12 and everyone["unacknowledged"] == 12
    names = {row["title"]: row["owner_name"] for row in everyone["items"]}
    assert names["Other personal 1"] == actors.owner.display_name
    assert names["Other desk 6"] is None  # team rows are identified by their workspace
    # Broad administrative authority is unchanged: an explicit acknowledgement still works.
    foreign = unrelated[0].id
    ack = await client.post(f"/api/warning/alerts/{foreign}/ack", headers=bearer(token))
    assert ack.status_code == 200 and ack.json()["created_by"] == str(actors.owner.id)

    async with team_service(container) as service:
        await service.remove_member(second, actors.team.id, admin.id, CONTEXT)
    revoked = (await client.get("/api/warning/alerts", headers=bearer(token))).json()
    assert [row["id"] for row in revoked["items"]] == [str(own.id)]
    assert revoked["unacknowledged"] == 1


async def test_only_administrators_may_request_every_users_alerts(
    client: AsyncClient, container: Container, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    peer = _alert(container, "Peer private", 5, created_by=actors.peer.id, team_id=None)
    async with container.session_factory() as session:
        session.add(_alert_row(peer))
        await session.commit()
    token = await login_token(client, actors.owner.email, USER_PASSWORD)
    forbidden = await client.get("/api/warning/alerts?scope=all", headers=bearer(token))
    assert forbidden.status_code == 403
    assert "administrator" in forbidden.json()["error"]["message"].lower()
    unknown = await client.get("/api/warning/alerts?scope=team", headers=bearer(token))
    assert unknown.status_code == 422
    default = (await client.get("/api/warning/alerts", headers=bearer(token))).json()
    assert default["items"] == [] and default["unacknowledged"] == 0


async def _jobs(container: Container, rows: list) -> None:
    async with container.session_factory() as session:
        repository = SqlReportJobRepository(session)
        for row in rows:
            await repository.add(row)
        await session.commit()


def _job(owner: User, minutes: int, team_id=None):
    at = NOW + timedelta(minutes=minutes)
    payload = {"schema_version": 1, "summary": SUMMARY, "input": {"scope": {}}}
    return job(owner_id=owner.id, team_id=team_id, payload=payload, created_at=at, updated_at=at)


async def test_admin_research_progress_defaults_to_own_work_and_widens_explicitly(
    client: AsyncClient, container: Container, admin: User, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    second = await _join(container, admin, actors)
    own = _job(admin, 0)
    team = _job(actors.owner, 1, actors.team.id)
    unrelated = [_job(actors.owner, 10 + n) for n in range(3)]
    unrelated += [_job(actors.outsider, 20 + n, actors.other.id) for n in range(3)]
    await _jobs(container, [own, team, *unrelated])
    headers = bearer(await login_token(client, admin.email, ADMIN_PASSWORD))

    first = (await client.get("/api/report-jobs?limit=1", headers=headers)).json()
    assert [row["id"] for row in first["items"]] == [str(team.id)]
    following = (
        await client.get(
            "/api/report-jobs", params={"limit": 1, "cursor": first["next_cursor"]}, headers=headers
        )
    ).json()
    assert [row["id"] for row in following["items"]] == [str(own.id)]
    assert following["next_cursor"] is None
    assert following["items"][0]["owner_id"] == str(admin.id)
    assert following["items"][0]["owner_name"] == admin.display_name

    everyone = (await client.get("/api/report-jobs?scope=all&limit=50", headers=headers)).json()
    assert len(everyone["items"]) == 8
    by_id = {row["id"]: row for row in everyone["items"]}
    assert by_id[str(unrelated[0].id)]["owner_name"] == actors.owner.display_name
    assert by_id[str(unrelated[0].id)]["team_id"] is None
    assert by_id[str(unrelated[3].id)]["team_id"] == str(actors.other.id)
    assert by_id[str(unrelated[0].id)]["owner_id"] == str(actors.owner.id)
    assert by_id[str(unrelated[3].id)]["owner_name"] is None

    async with team_service(container) as service:
        await service.remove_member(second, actors.team.id, admin.id, CONTEXT)
    revoked = (await client.get("/api/report-jobs", headers=headers)).json()
    assert [row["id"] for row in revoked["items"]] == [str(own.id)]


async def test_only_administrators_may_request_every_users_research_progress(
    client: AsyncClient, container: Container, warning_actors: WarningActors
) -> None:
    actors = warning_actors
    await _jobs(container, [_job(actors.peer, 0)])
    headers = bearer(await login_token(client, actors.owner.email, USER_PASSWORD))
    forbidden = await client.get("/api/report-jobs?scope=all", headers=headers)
    assert forbidden.status_code == 403
    assert (await client.get("/api/report-jobs?scope=x", headers=headers)).status_code == 422
    assert (await client.get("/api/report-jobs", headers=headers)).json()["items"] == []
