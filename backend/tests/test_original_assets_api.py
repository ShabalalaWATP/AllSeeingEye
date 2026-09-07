"""Deliberate original retention, final access checks and exact-version delivery."""

import io
import json
import zipfile
from datetime import timedelta
from uuid import UUID

import pytest

import ase.application.reports.original_assets as service
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from helpers import USER_PASSWORD, bearer, login_token
from original_asset_helpers import ORIGINAL, asset_path, original_report, reserve_body, retained
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for


async def test_original_roundtrip_is_inert_explicitly_selected_and_deleted(client, container, user):
    record, version = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = await retained(client, record, headers)
    assert asset["status"] == "active" and asset["filename"] == "source.txt"
    assert asset["report_version_id"] == str(version.id)
    assert "session_family_id" not in asset
    path = f"{asset_path(record)}/{asset['id']}"
    download = await client.get(f"{path}/content", headers=headers)
    assert download.status_code == 200 and download.content == ORIGINAL
    assert download.headers["content-type"] == "application/octet-stream"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["x-content-type-options"] == "nosniff"
    package = await client.post(
        f"/api/reports/{record.id}/selected-evidence-package",
        headers=headers,
        json={"version_number": 1, "asset_ids": [asset["id"]]},
    )
    assert package.status_code == 200, package.text
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["original_assets_included"] is True
        assert archive.read(f"originals/{asset['id']}.bin") == ORIGINAL
        assert b"session_family_id" not in package.content
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(f"{path}/content", headers=headers)).status_code == 404
    assert (await client.get(f"{asset_path(record)}?version_number=1", headers=headers)).json() == {
        "items": [],
    }
    async with container.session_factory() as session:
        tombstone = await SqlOriginalAssetRepository(session).get(UUID(asset["id"]))
        assert tombstone.status == "deleted" and not tombstone.permitted_use


@pytest.mark.parametrize("content", [b"wrong original", ORIGINAL[:-1], ORIGINAL + b"x"])
async def test_wrong_or_oversized_upload_clears_reservation(client, container, user, content):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = (await client.post(asset_path(record), headers=headers, json=reserve_body())).json()
    response = await client.put(
        f"{asset_path(record)}/{asset['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=content,
    )
    assert response.status_code in {400, 413, 422}, response.text
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        assert await repository.pending_count() == 0
        assert await repository.content(UUID(asset["id"])) is None


async def test_new_session_cannot_use_existing_reservation(client, container, user):
    record, _ = await original_report(container, user)
    old = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = (await client.post(asset_path(record), headers=old, json=reserve_body())).json()
    fresh = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.put(
        f"{asset_path(record)}/{asset['id']}/content",
        headers={**fresh, "Content-Type": "application/octet-stream"},
        content=ORIGINAL,
    )
    assert response.status_code == 404
    assert (
        await client.delete(f"{asset_path(record)}/{asset['id']}", headers=fresh)
    ).status_code == 204


async def test_revocation_during_body_consumption_cannot_retain(
    client,
    container,
    admin,
    user,
):
    team = await team_for(container, admin, user)
    record, _ = await original_report(container, user, team.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = (await client.post(asset_path(record), headers=headers, json=reserve_body())).json()

    async def body():
        yield ORIGINAL[:5]
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        yield ORIGINAL[5:]

    response = await client.put(
        f"{asset_path(record)}/{asset['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=body(),
    )
    assert response.status_code == 404, response.text
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        assert await repository.pending_count() == 0
        assert await repository.content(UUID(asset["id"])) is None


async def test_expiry_and_foreign_report_version_are_not_downloadable(
    client,
    container,
    user,
    clock,
):
    record, _ = await original_report(container, user)
    other, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = await retained(client, record, headers)
    assert (
        await client.get(
            f"{asset_path(other)}/{asset['id']}/content",
            headers=headers,
        )
    ).status_code == 404
    response = await client.post(
        f"/api/reports/{record.id}/selected-evidence-package",
        headers=headers,
        json={"version_number": 2, "asset_ids": [asset["id"]]},
    )
    assert response.status_code == 404
    clock.advance(timedelta(days=30))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.get(
            f"{asset_path(record)}/{asset['id']}/content",
            headers=headers,
        )
    ).status_code == 404
    # A successful list commits physical expiry even after a denied download rolls back.
    await client.get(f"{asset_path(record)}?version_number=1", headers=headers)
    async with container.session_factory() as session:
        assert await SqlOriginalAssetRepository(session).content(UUID(asset["id"])) is None


async def test_reservations_count_before_upload_and_deleted_records_remain_bounded(
    client,
    container,
    user,
    monkeypatch,
):
    monkeypatch.setattr(service, "MAX_PERSONAL_RECORDS", 2)
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = (await client.post(asset_path(record), headers=headers, json=reserve_body())).json()
    second = (await client.post(asset_path(record), headers=headers, json=reserve_body())).json()
    assert (
        await client.post(asset_path(record), headers=headers, json=reserve_body())
    ).status_code == 429
    await client.delete(f"{asset_path(record)}/{first['id']}", headers=headers)
    await client.delete(f"{asset_path(record)}/{second['id']}", headers=headers)
    assert (
        await client.post(asset_path(record), headers=headers, json=reserve_body())
    ).status_code == 422
