"""Intake admission, disconnection and physical expiry independent of dashboard traffic."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import Request

import ase.api.routers.original_assets as asset_routes
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.api.original_upload import finish_connected
from ase.application.reports.original_assets import OriginalAssets
from ase.container.original_asset_expiry import expire_original_assets
from helpers import USER_PASSWORD, bearer, login_token
from original_asset_helpers import ORIGINAL, asset_path, original_report, reserve_body, retained


async def test_unauthenticated_original_upload_does_not_read_body(client):
    consumed = False

    async def body():
        nonlocal consumed
        consumed = True
        yield b"private original"

    response = await client.put(
        f"/api/reports/{uuid4()}/original-assets/{uuid4()}/content",
        headers={"Content-Type": "application/octet-stream"},
        content=body(),
    )
    assert response.status_code == 401
    assert consumed is False


async def test_disconnected_after_body_cancels_final_retention_work():
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def operation():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def receive():
        await started.wait()
        return {"type": "http.disconnect"}

    request = Request({"type": "http"}, receive)
    with pytest.raises(asyncio.CancelledError):
        await finish_connected(request, operation())
    assert cancelled.is_set()


async def test_final_download_rechecks_delete_during_preceding_session_guard(
    client,
    container,
    user,
    monkeypatch,
):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = await retained(client, record, headers)
    original = OriginalAssets.recheck

    async def delete_then_recheck(self, claims, selected):
        async with container.session_factory() as session:
            await SqlOriginalAssetRepository(session).delete(
                UUID(asset["id"]), container.clock.now()
            )
            await session.commit()
        return await original(self, claims, selected)

    monkeypatch.setattr(OriginalAssets, "recheck", delete_then_recheck)
    response = await client.get(f"{asset_path(record)}/{asset['id']}/content", headers=headers)
    assert response.status_code == 404


async def test_periodic_cleanup_physically_removes_bytes_without_requests(
    client,
    container,
    user,
    clock,
):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = await retained(client, record, headers)
    clock.advance(timedelta(days=30))
    worker = asyncio.create_task(expire_original_assets(container.session_factory, clock))
    try:
        async with asyncio.timeout(5):
            while True:
                async with container.session_factory() as session:
                    found = await SqlOriginalAssetRepository(session).get(UUID(asset["id"]))
                    if found.status == "expired":
                        assert await SqlOriginalAssetRepository(session).content(found.id) is None
                        break
                await asyncio.sleep(0.01)
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
    assert worker.cancelled()


async def test_reused_upload_reservation_does_not_consume_another_body(client, container, user):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    asset = await retained(client, record, headers)
    consumed = False

    async def body():
        nonlocal consumed
        consumed = True
        yield ORIGINAL

    response = await client.put(
        f"{asset_path(record)}/{asset['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=body(),
    )
    assert response.status_code == 409 and consumed is False


async def test_original_bytes_above_json_cap_are_streamed(client, container, user):
    content = b"x" * (128 * 1024)
    record, _ = await original_report(container, user, content=content)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    reserved = await client.post(
        asset_path(record),
        headers=headers,
        json=reserve_body(byte_count=len(content)),
    )
    assert reserved.status_code == 201
    response = await client.put(
        f"{asset_path(record)}/{reserved.json()['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=content,
    )
    assert response.status_code == 200, response.text


async def test_upload_timeout_includes_final_retention_and_releases_reservation(
    client,
    container,
    user,
    monkeypatch,
):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    reserved = await client.post(asset_path(record), headers=headers, json=reserve_body())
    started = asyncio.Event()

    async def delayed_finish(*args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(OriginalAssets, "finish_upload", delayed_finish)
    monkeypatch.setattr(asset_routes, "UPLOAD_TIMEOUT_SECONDS", 0.05)
    response = await client.put(
        f"{asset_path(record)}/{reserved.json()['id']}/content",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=ORIGINAL,
    )
    assert response.status_code == 422 and started.is_set()
    async with container.session_factory() as session:
        assert await SqlOriginalAssetRepository(session).pending_count() == 0
