"""Measurement revisions survive persistence, retain history and enforce integrity."""

from uuid import UUID

from sqlalchemy import update

from ase.adapters.persistence.map_view_models import MapViewRevisionRow
from ase.domain.map_measurement import METHOD
from helpers import USER_PASSWORD, bearer, login_token
from test_map_views_api import body
from test_report_team_scope import save_team_report


async def test_saved_measurement_history_survives_changes_and_detects_stored_tampering(
    client, container, user
):
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(report.id)
    measurement = {
        "mode": "area",
        "method": METHOD,
        "points": [[179.987654321, 88.5], [-179.7654321, 88.5], [180, 90]],
    }
    payload["state"]["measurement"] = measurement
    created = await client.post("/api/map/views", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    saved = created.json()
    revision = saved["revision"]
    assert revision["state"]["measurement"] == measurement
    assert revision["state"]["aoi"] is None
    path = f"/api/map/views/{saved['view']['id']}"
    assert (await client.get(path, headers=headers)).json()["revision"] == revision
    updated = await client.patch(
        path,
        headers=headers,
        json={
            "base_revision_id": revision["id"],
            "version_number": 1,
            "title": payload["title"],
            "state": {**revision["state"], "measurement": None},
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"]["state"]["measurement"] is None
    assert updated.json()["revision"]["content_sha256"] != revision["content_sha256"]
    historical = await client.get(f"{path}/revisions/{revision['id']}", headers=headers)
    assert historical.json()["revision"] == revision
    # A changed point with the old digest must fail closed on an authorised read.
    async with container.session_factory() as session:
        row = await session.get(MapViewRevisionRow, UUID(revision["id"]))
        state = dict(row.state)
        state["measurement"] = {**measurement, "points": [[0, 0], [1, 1], [2, 0]]}
        await session.execute(
            update(MapViewRevisionRow)
            .where(MapViewRevisionRow.id == UUID(revision["id"]))
            .values(state=state)
        )
        await session.commit()
    rejected = await client.get(f"{path}/revisions/{revision['id']}", headers=headers)
    assert rejected.status_code == 409
    assert "integrity" in rejected.text


async def test_invalid_measurement_requests_never_create_a_map(client, container, user):
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(report.id)
    for change in ({"points": [[0, 0]] * 33}, {"metres": 123}, {"points": [[True, 0]]}):
        payload["state"]["measurement"] = {
            "mode": "distance",
            "method": METHOD,
            "points": [[0, 0]],
            **change,
        }
        rejected = await client.post("/api/map/views", headers=headers, json=payload)
        assert rejected.status_code == 422, rejected.text
    page = await client.get(f"/api/map/views?report_id={report.id}", headers=headers)
    assert page.json()["total"] == 0
