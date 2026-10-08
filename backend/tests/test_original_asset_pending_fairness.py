"""Upload reservations are capped per uploader, with the shared cap kept as a backstop."""

from datetime import timedelta

import ase.application.reports.original_assets as service
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from helpers import USER_PASSWORD, bearer, create_user, login_token
from original_asset_helpers import asset_path, original_report, reserve_body


async def _uploader(client, container, email):
    account = await create_user(container, email=email, password=USER_PASSWORD)
    record, _ = await original_report(container, account)
    headers = bearer(await login_token(client, account.email, USER_PASSWORD))
    return account, record, headers


async def _reserve(client, record, headers):
    return await client.post(asset_path(record), headers=headers, json=reserve_body())


async def test_one_uploader_cannot_hold_every_pending_slot(client, container, monkeypatch):
    monkeypatch.setattr(service, "MAX_PENDING_UPLOADS", 2)
    heavy, heavy_record, heavy_headers = await _uploader(client, container, "heavy@example.com")
    _, second_record, second_headers = await _uploader(client, container, "second@example.com")
    _, third_record, third_headers = await _uploader(client, container, "third@example.com")

    assert (await _reserve(client, heavy_record, heavy_headers)).status_code == 201
    # Previously a single account could take both shared slots.
    refused = await _reserve(client, heavy_record, heavy_headers)
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "rate_limited"
    assert (await _reserve(client, second_record, second_headers)).status_code == 201
    # The shared cap still bounds intake across every account.
    assert (await _reserve(client, third_record, third_headers)).status_code == 429
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        assert await repository.pending_count() == 2
        assert await repository.pending_count(heavy.id) == 1


async def test_an_expired_reservation_frees_the_uploader_slot(client, container):
    _, record, headers = await _uploader(client, container, "returning@example.com")
    assert (await _reserve(client, record, headers)).status_code == 201
    assert (await _reserve(client, record, headers)).status_code == 429
    container.clock.advance(timedelta(minutes=3))
    assert (await _reserve(client, record, headers)).status_code == 201
