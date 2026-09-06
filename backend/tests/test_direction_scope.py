"""No personal/team direction data leaks through lists, linked IDs or mutation routes."""

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from direction_scope_helpers import DirectionActors, area, direction_actors, plan


@pytest.fixture
async def actors(
    client: AsyncClient, container: Container, admin: User, user: User
) -> DirectionActors:
    return await direction_actors(client, container, user)


async def test_lists_include_only_owned_and_current_team_records(
    client: AsyncClient, actors: DirectionActors
) -> None:
    for route, body in (("aois", area), ("plans", plan)):
        for name, team, headers in (
            ("Private", None, actors.owner),
            ("Team", actors.team, actors.owner),
            ("Other", actors.other_team, actors.admin),
            ("Own", None, actors.member),
        ):
            response = await client.post(
                f"/api/direction/{route}", json=body(name, team), headers=headers
            )
            assert response.status_code == 201, response.text
        listed = await client.get(f"/api/direction/{route}", headers=actors.member)
        assert {item["name"] for item in listed.json()["items"]} == {"Own", "Team"}
        assert (await client.get(f"/api/direction/{route}", headers=actors.outsider)).json()[
            "items"
        ] == []
        assert (
            len((await client.get(f"/api/direction/{route}", headers=actors.admin)).json()["items"])
            == 4
        )


async def test_direct_plan_and_mutation_ids_do_not_disclose_other_scopes(
    client: AsyncClient, actors: DirectionActors
) -> None:
    for team in (None, actors.other_team):
        created = await client.post(
            "/api/direction/plans", json=plan(team=team), headers=actors.admin
        )
        plan_id = created.json()["id"]
        for headers in (actors.owner, actors.manager, actors.outsider):
            assert (
                await client.get(f"/api/direction/plans/{plan_id}", headers=headers)
            ).status_code == 404
            assert (
                await client.put(
                    f"/api/direction/plans/{plan_id}", json=plan(team=team), headers=headers
                )
            ).status_code == 404
            assert (
                await client.delete(f"/api/direction/plans/{plan_id}", headers=headers)
            ).status_code == 404
        created_area = await client.post(
            "/api/direction/aois", json=area(team=team), headers=actors.admin
        )
        assert (
            await client.delete(
                f"/api/direction/aois/{created_area.json()['id']}", headers=actors.owner
            )
        ).status_code == 404


async def test_member_reads_but_only_creator_or_designated_manager_edits(
    client: AsyncClient, actors: DirectionActors
) -> None:
    response = await client.post(
        "/api/direction/plans", json=plan(team=actors.team), headers=actors.owner
    )
    plan_id = response.json()["id"]
    assert (
        await client.get(f"/api/direction/plans/{plan_id}", headers=actors.member)
    ).status_code == 200
    assert (
        await client.put(
            f"/api/direction/plans/{plan_id}",
            json=plan("Denied", actors.team),
            headers=actors.member,
        )
    ).status_code == 403
    assert (
        await client.put(
            f"/api/direction/plans/{plan_id}",
            json=plan("Manager edit", actors.team),
            headers=actors.manager,
        )
    ).status_code == 200
    # Global manager capability without leadership in this team cannot mutate others' work.
    assert (
        await client.put(
            f"/api/teams/{actors.team}/members",
            json={"email": actors.manager_user.email},
            headers=actors.admin,
        )
    ).status_code == 200
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=actors.manager)
    ).status_code == 403
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=actors.owner)
    ).status_code == 204


async def test_linked_area_must_have_matching_scope_even_for_admin(
    client: AsyncClient, actors: DirectionActors
) -> None:
    personal = await client.post("/api/direction/aois", json=area(), headers=actors.owner)
    personal_id = personal.json()["id"]
    assert (
        await client.post("/api/direction/plans", json=plan(aoi=personal_id), headers=actors.owner)
    ).status_code == 201
    assert (
        await client.post("/api/direction/plans", json=plan(aoi=personal_id), headers=actors.member)
    ).status_code == 404
    assert (
        await client.post("/api/direction/plans", json=plan(aoi=personal_id), headers=actors.admin)
    ).status_code == 422
    team_area = await client.post(
        "/api/direction/aois", json=area(team=actors.team), headers=actors.owner
    )
    team_area_id = team_area.json()["id"]
    assert (
        await client.post(
            "/api/direction/plans",
            json=plan(team=actors.team, aoi=team_area_id),
            headers=actors.member,
        )
    ).status_code == 201
    assert (
        await client.post(
            "/api/direction/plans", json=plan(aoi=team_area_id), headers=actors.member
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/direction/plans",
            json=plan(team=actors.other_team, aoi=team_area_id),
            headers=actors.admin,
        )
    ).status_code == 422


async def test_archive_preserves_read_and_blocks_ordinary_writes(
    client: AsyncClient, actors: DirectionActors
) -> None:
    response = await client.post(
        "/api/direction/plans", json=plan(team=actors.team), headers=actors.owner
    )
    plan_id = response.json()["id"]
    assert (
        await client.patch(
            f"/api/teams/{actors.team}", json={"is_active": False}, headers=actors.admin
        )
    ).status_code == 200
    for headers in (actors.owner, actors.member, actors.manager):
        assert (
            await client.get(f"/api/direction/plans/{plan_id}", headers=headers)
        ).status_code == 200
        assert (
            await client.post("/api/direction/aois", json=area(team=actors.team), headers=headers)
        ).status_code == 403
        assert (
            await client.post("/api/direction/plans", json=plan(team=actors.team), headers=headers)
        ).status_code == 403
        assert (
            await client.delete(f"/api/direction/plans/{plan_id}", headers=headers)
        ).status_code == 403
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=actors.admin)
    ).status_code == 204


async def test_revoked_member_loses_authored_team_work_and_cannot_change_scope(
    client: AsyncClient, actors: DirectionActors, user: User
) -> None:
    response = await client.post(
        "/api/direction/plans", json=plan(team=actors.team), headers=actors.owner
    )
    plan_id = response.json()["id"]
    assert (
        await client.put(f"/api/direction/plans/{plan_id}", json=plan(), headers=actors.owner)
    ).status_code == 422
    assert (
        await client.delete(f"/api/teams/{actors.team}/members/{user.id}", headers=actors.admin)
    ).status_code == 204
    assert (
        await client.get(f"/api/direction/plans/{plan_id}", headers=actors.owner)
    ).status_code == 404
    assert (
        await client.delete(f"/api/direction/plans/{plan_id}", headers=actors.owner)
    ).status_code == 404
    assert (
        await client.post("/api/direction/plans", json=plan(team=actors.team), headers=actors.owner)
    ).status_code == 404
