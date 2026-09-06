"""Saved-map API contracts preserve scope, exact revisions and strict geometry bounds."""

import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_report_team_scope import save_team_report, team_for


def body(report_id):
    return {
        "report_id": str(report_id),
        "version_number": 1,
        "title": "Northern evidence",
        "state": {"camera": {"longitude": 179, "latitude": 60, "zoom": 4}},
    }


async def test_saved_revisions_are_exact_conflicts_are_explicit_and_archive_retains_history(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post("/api/map/views", headers=headers, json=body(report.id))
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    saved = created.json()
    path = f"/api/map/views/{saved['view']['id']}"
    revision = saved["revision"]
    assert revision["number"] == 1 and revision["report_version_number"] == 1
    assert saved["view"]["team_id"] is None
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        original_version = await reports.get_version(report.id, 1)
        assert original_version is not None
        report.latest_version = 2
        await reports.add_version(report, replace(original_version, id=uuid4(), number=2))
        await session.commit()
    patch = {
        "base_revision_id": revision["id"],
        "version_number": 1,
        "title": "Revised angle",
        "state": {**revision["state"], "projection": "mercator"},
    }
    updated = await client.patch(path, headers=headers, json=patch)
    assert updated.status_code == 200, updated.text
    assert updated.headers["cache-control"] == "no-store"
    assert updated.json()["revision"]["id"] != revision["id"]
    assert updated.json()["revision"]["number"] == 2
    assert (await client.patch(path, headers=headers, json=patch)).status_code == 409
    historical = await client.get(f"{path}/revisions/{revision['id']}", headers=headers)
    assert historical.status_code == 200
    assert historical.json()["revision"] == revision
    assert historical.headers["cache-control"] == "no-store"
    latest = await client.get(path, headers=headers)
    assert latest.json()["revision"]["title"] == "Revised angle"
    assert latest.headers["cache-control"] == "no-store"
    page = await client.get(f"/api/map/views?report_id={report.id}&limit=1", headers=headers)
    assert page.status_code == 200 and page.json()["total"] == 1
    assert "state" not in page.json()["items"][0]
    assert page.headers["cache-control"] == "no-store"
    archived = await client.delete(path, headers=headers)
    assert archived.status_code == 204 and archived.headers["cache-control"] == "no-store"
    assert (await client.get(f"/api/map/views?report_id={report.id}", headers=headers)).json()[
        "total"
    ] == 0
    assert (
        await client.get(f"{path}/revisions/{revision['id']}", headers=headers)
    ).status_code == 200


async def test_private_views_do_not_grant_other_accounts_report_access(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    report = await save_team_report(container, admin, None)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post("/api/map/views", headers=admin_headers, json=body(report.id))
    assert created.status_code == 201, created.text
    saved = created.json()
    path = f"/api/map/views/{saved['view']['id']}"
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for url in (
        path,
        f"{path}/revisions/{saved['revision']['id']}",
        f"/api/map/views?report_id={report.id}",
    ):
        assert (await client.get(url, headers=headers)).status_code == 404
    assert (
        await client.post("/api/map/views", headers=headers, json=body(report.id))
    ).status_code == 404
    assert (await client.delete(path, headers=headers)).status_code == 404
    assert (await client.get(path)).status_code == 401


async def test_team_scope_is_inherited_and_membership_revocation_denies_history(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    team = await team_for(container, admin, user)
    report = await save_team_report(container, user, team.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post("/api/map/views", headers=headers, json=body(report.id))
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["view"]["team_id"] == str(team.id)
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    path = f"/api/map/views/{saved['view']['id']}"
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (
        await client.get(f"{path}/revisions/{saved['revision']['id']}", headers=headers)
    ).status_code == 404
    assert (
        await client.get(f"/api/map/views?report_id={report.id}", headers=headers)
    ).status_code == 404


@pytest.mark.parametrize(
    "change",
    [
        {"team_id": str(uuid4())},
        {"version_number": True},
        {"version_number": 0},
        {"title": "   "},
        {"state": {"camera": {"longitude": 0, "latitude": 91, "zoom": 4}}},
        {"state": {"camera": {"longitude": True, "latitude": 0, "zoom": 4}}},
        {"state": {"camera": {"longitude": 0, "latitude": 0, "zoom": "4"}}},
        {"state": {"camera": {"longitude": 0, "latitude": 0, "zoom": 4}, "secret": "unsupported"}},
        {
            "state": {
                "camera": {"longitude": 0, "latitude": 0, "zoom": 4},
                "include_unknown_dates": "yes",
            }
        },
        {
            "state": {
                "camera": {"longitude": 0, "latitude": 0, "zoom": 4},
                "published_since": "2026-09-01T12:00:00",
            }
        },
        {
            "state": {
                "camera": {"longitude": 0, "latitude": 0, "zoom": 4},
                "source_ids": ["same", "same"],
            }
        },
        {
            "state": {
                "camera": {"longitude": 0, "latitude": 0, "zoom": 4},
                "aoi": {"type": "FeatureCollection", "features": []},
            }
        },
    ],
)
async def test_invalid_state_and_scope_overrides_are_validation_errors(
    client: AsyncClient,
    container: Container,
    user: User,
    change: dict,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = {**body(report.id), **deepcopy(change)}
    response = await client.post("/api/map/views", headers=headers, json=payload)
    assert response.status_code == 422, response.text
    assert response.headers["cache-control"] == "no-store"
    assert (await client.get(f"/api/map/views?report_id={report.id}", headers=headers)).json()[
        "total"
    ] == 0


async def test_unknown_revision_cannot_be_substituted_and_revoked_family_is_rechecked(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    report = await save_team_report(container, user, None)
    token = await login_token(client, user.email, USER_PASSWORD)
    headers = bearer(token)
    assert (
        await client.post(
            "/api/map/views", headers=headers, json={**body(report.id), "version_number": 99}
        )
    ).status_code == 404
    created = await client.post("/api/map/views", headers=headers, json=body(report.id))
    assert created.status_code == 201, created.text
    path = f"/api/map/views/{created.json()['view']['id']}"
    assert (await client.get(f"{path}/revisions/{uuid4()}", headers=headers)).status_code == 404
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id, container.clock.now()
        )
        await session.commit()
    assert (await client.get(path, headers=headers)).status_code == 401
    assert (await client.delete(path, headers=headers)).status_code == 401


async def test_authentication_precedes_geometry_validation(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id,
            container.clock.now(),
        )
        await session.commit()

    def forbidden_validation(raw):
        raise AssertionError("Unauthorised requests must not validate geometry")

    monkeypatch.setattr("ase.api.schemas_map_views.state_from_dict", forbidden_validation)
    for headers in ({}, bearer(token)):
        response = await client.post("/api/map/views", headers=headers, json=body(uuid4()))
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"


async def test_local_overlay_roundtrips_canonical_coordinates_labels_and_metadata(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(report.id)
    payload["state"]["overlays"] = [
        {
            "geometry": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"label": "نقشه"},
                        "geometry": {"type": "Point", "coordinates": [-179, 89]},
                    }
                ],
            },
            "source": "Operator reference",
            "dataset_date": "2026-09-01",
            "attribution": "Local synthetic fixture",
            "precision": "unknown",
            "visible": False,
        }
    ]
    features = payload["state"]["overlays"][0]["geometry"]["features"]
    features.extend(
        [{**deepcopy(features[0]), "properties": {"label": "x" * 300}} for _ in range(220)]
    )
    assert len(json.dumps(payload).encode("utf-8")) > 64 * 1024
    result = await client.post("/api/map/views", headers=headers, json=payload)
    assert result.status_code == 201, result.text
    saved = result.json()
    overlay = saved["revision"]["state"]["overlays"][0]
    assert overlay["geometry"]["features"][0]["geometry"]["coordinates"] == [-179, 89]
    assert overlay["geometry"]["features"][0]["properties"]["label"] == "نقشه"
    assert not overlay["visible"] and overlay["precision"] == "unknown"
    loaded = await client.get(f"/api/map/views/{saved['view']['id']}", headers=headers)
    assert loaded.json()["revision"]["state"]["overlays"][0] == overlay
    payload["state"]["overlays"][0]["geometry"]["features"][0]["geometry"]["coordinates"] = [0, 91]
    assert (await client.post("/api/map/views", headers=headers, json=payload)).status_code == 422
