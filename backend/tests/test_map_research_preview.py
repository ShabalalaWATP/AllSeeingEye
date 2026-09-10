"""Map previews disclose only authorised exact geometry and never collect it."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import update

from ase.adapters.persistence.map_view_models import MapViewRevisionRow
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_map_research_origin import AREA, setup
from test_report_team_scope import team_for
from test_research_plan import NOW, QUERY
from test_saved_map_views import revise


def body(view, revision):
    return {
        "question": "Which observations cover this area?",
        "since": QUERY.since.isoformat(),
        "until": NOW.isoformat(),
        "map_view_id": str(view.id),
        "map_revision_id": str(revision.id),
    }


async def headers(client, user):
    password = ADMIN_PASSWORD if user.is_admin else USER_PASSWORD
    return bearer(await login_token(client, user.email, password))


async def test_preview_retains_exact_area_without_collecting(client, container, user, monkeypatch):
    parent, claims, view, revision, _ = await setup(client, container, user)
    await revise(container, claims, view, revision)
    collect = AsyncMock(side_effect=AssertionError("Preview must not collect"))
    monkeypatch.setattr(container.research, "collect", collect)
    response = await client.post(
        "/api/research/runs/plan", json=body(view, revision), headers=await headers(client, user)
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert result["area"]["sha256"] == AREA.sha256
    assert result["map_origin"]["revision_id"] == str(revision.id)
    assert result["map_origin"]["report_id"] == str(parent.id)
    assert result["map_origin"]["area"] == result["area"]
    assert result["tasks"]
    assert {task["source_id"] for task in result["tasks"] if task["supported"]} == {
        "research-copernicus-footprints",
        "research-retained-area-feeds",
    }
    assert result["model_calls"] == result["translation_calls"] == 0
    collect.assert_not_awaited()


@pytest.mark.parametrize("change", [{"map_revision_id": None}, {"area": {}}, {"country_iso": "GB"}])
async def test_preview_rejects_incomplete_or_ambiguous_area(client, container, user, change):
    _, _, view, revision, _ = await setup(client, container, user)
    response = await client.post(
        "/api/research/runs/plan",
        json={**body(view, revision), **change},
        headers=await headers(client, user),
    )
    assert response.status_code == 422


async def test_preview_cannot_copy_another_private_origin_even_as_admin(
    client, container, user, admin
):
    _, _, view, revision, _ = await setup(client, container, user)
    response = await client.post(
        "/api/research/runs/plan", json=body(view, revision), headers=await headers(client, admin)
    )
    assert response.status_code == 422
    assert "geometry" not in response.text


async def test_team_preview_rechecks_membership_and_does_not_change_scope(
    client, container, user, admin
):
    team = await team_for(container, admin, user)
    _, _, view, revision, _ = await setup(client, container, user, team.id)
    auth = await headers(client, user)
    payload = {**body(view, revision), "team_id": str(team.id)}
    response = await client.post("/api/research/runs/plan", json=payload, headers=auth)
    assert response.status_code == 200
    private = await client.post("/api/research/runs/plan", json=body(view, revision), headers=auth)
    assert private.status_code == 422
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    revoked = await client.post("/api/research/runs/plan", json=payload, headers=auth)
    assert revoked.status_code == 404
    assert revoked.headers["cache-control"] == "no-store"
    assert "geometry" not in revoked.text


async def test_preview_hides_another_users_map(client, container, user, admin):
    _, _, view, revision, _ = await setup(client, container, admin)
    response = await client.post(
        "/api/research/runs/plan", json=body(view, revision), headers=await headers(client, user)
    )
    assert response.status_code == 404
    assert "geometry" not in response.text


async def test_preview_rejects_tampered_revision(client, container, user):
    _, _, view, revision, _ = await setup(client, container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(MapViewRevisionRow)
            .where(MapViewRevisionRow.id == revision.id)
            .values(title="Tampered title")
        )
        await session.commit()
    response = await client.post(
        "/api/research/runs/plan", json=body(view, revision), headers=await headers(client, user)
    )
    assert response.status_code == 409
    assert "geometry" not in response.text


async def test_preview_rejects_revoked_session(client, container, user):
    _, _, view, revision, _ = await setup(client, container, user)
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.refresh_tokens.revoke_family(claims.family_id, container.clock.now())
        await repos.uow.commit()
    response = await client.post(
        "/api/research/runs/plan", json=body(view, revision), headers=bearer(token)
    )
    assert response.status_code == 401
    assert "geometry" not in response.text
