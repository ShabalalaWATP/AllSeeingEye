"""Discarded reservations cannot consume another uploader's live retention capacity."""

from datetime import timedelta

import pytest

import ase.application.reports.original_assets as service
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.domain.teams import MembershipRole
from helpers import USER_PASSWORD, bearer, create_user, login_token
from original_asset_helpers import ORIGINAL, asset_path, original_report, reserve_body, retained
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for


async def _discard(client, container, record, headers, method):
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 201, response.text
    path = f"{asset_path(record)}/{response.json()['id']}"
    if method == "delete":
        assert (await client.delete(path, headers=headers)).status_code == 204
    elif method == "failed_upload":
        response = await client.put(
            f"{path}/content",
            headers={**headers, "Content-Type": "application/octet-stream"},
            content=b"x" * len(ORIGINAL),
        )
        assert response.status_code == 422, response.text
    else:
        container.clock.advance(timedelta(minutes=3))
        response = await client.get(f"{asset_path(record)}?version_number=1", headers=headers)
        assert response.status_code == 200 and response.json() == {"items": []}


@pytest.mark.parametrize("method", ["delete", "failed_upload", "expiry"])
async def test_discarded_reservations_leave_team_capacity_for_another_member(
    client, container, admin, user, monkeypatch, method
):
    monkeypatch.setattr(service, "MAX_TEAM_RECORDS", 2)
    monkeypatch.setattr(service, "MAX_RETIRED_RECORDS_PER_USER", 2)
    team = await team_for(container, admin, user)
    peer = await create_user(container, email="peer-originals@example.com", password=USER_PASSWORD)
    async with team_service(container) as teams:
        await teams.set_member(
            admin, team.id, email=peer.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    record, _ = await original_report(container, user, team.id)
    peer_record, _ = await original_report(container, peer, team.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for _ in range(2):
        await _discard(client, container, record, headers, method)

    async with container.session_factory() as session:
        assert await SqlOriginalAssetRepository(session).usage(team_id=team.id) == (2, 0)

    # A new report and login must not reset the uploader's cross-scope history budget.
    personal, _ = await original_report(container, user)
    fresh = bearer(await login_token(client, user.email, USER_PASSWORD))
    for blocked in (record, personal):
        response = await client.post(asset_path(blocked), headers=fresh, json=reserve_body())
        assert response.status_code == 422 and "discarded-record" in response.text

    peer_headers = bearer(await login_token(client, peer.email, USER_PASSWORD))
    asset = await retained(client, peer_record, peer_headers)
    response = await client.get(
        f"{asset_path(peer_record)}/{asset['id']}/content", headers=peer_headers
    )
    assert response.status_code == 200 and response.content == ORIGINAL


async def test_global_row_backstop_still_counts_scrubbed_history(
    client, container, user, monkeypatch
):
    monkeypatch.setattr(service, "MAX_GLOBAL_RECORDS", 1)
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    await _discard(client, container, record, headers, "delete")
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 422 and "storage or record limit" in response.text


@pytest.mark.parametrize("method", ["delete", "expiry"])
async def test_uploader_history_allowance_recovers_after_purge(
    client, container, user, monkeypatch, method
):
    monkeypatch.setattr(service, "MAX_RETIRED_RECORDS_PER_USER", 1)
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    await _discard(client, container, record, headers, method)
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 422 and "discarded-record" in response.text
    container.clock.advance(timedelta(days=30))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 201, response.text


async def test_active_originals_across_scopes_do_not_consume_history_allowance(
    client, container, admin, user, monkeypatch
):
    monkeypatch.setattr(service, "MAX_PERSONAL_RECORDS", 1)
    monkeypatch.setattr(service, "MAX_TEAM_RECORDS", 1)
    monkeypatch.setattr(service, "MAX_RETIRED_RECORDS_PER_USER", 1)
    first = await team_for(container, admin, user)
    async with team_service(container) as teams:
        second = await teams.create(admin, "Other originals", CONTEXT)
        await teams.set_member(
            admin, second.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for team_id in (None, first.id, second.id):
        record, _ = await original_report(container, user, team_id)
        assert (await retained(client, record, headers))["status"] == "active"
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        assert await repository.retired_count(user.id) == 0
        assert await repository.usage() == (3, 3 * len(ORIGINAL))


async def test_history_pressure_cannot_block_an_already_admitted_upload(
    client, container, user, monkeypatch
):
    monkeypatch.setattr(service, "MAX_RETIRED_RECORDS_PER_USER", 1)
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    await retained(client, record, headers)
    container.clock.advance(timedelta(days=30) - timedelta(minutes=1))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert response.status_code == 201, response.text
    path = f"{asset_path(record)}/{response.json()['id']}"

    async def body():
        container.clock.advance(timedelta(minutes=1))
        yield ORIGINAL

    response = await client.put(
        f"{path}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=body(),
    )
    assert response.status_code == 200 and response.json()["status"] == "active"
    async with container.session_factory() as session:
        assert await SqlOriginalAssetRepository(session).retired_count(user.id) == 1
