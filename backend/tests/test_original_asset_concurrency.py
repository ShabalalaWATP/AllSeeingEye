"""Real independent transactions cannot oversubscribe or consume an upload twice."""

import asyncio
from uuid import UUID

import pytest

import ase.application.reports.original_assets as asset_service
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.adapters.persistence.users import SqlUserRepository
from helpers import USER_PASSWORD, bearer, login_token
from original_asset_helpers import ORIGINAL, asset_path, original_report, reserve_body
from test_report_team_scope import team_for


@pytest.fixture
def settings(settings, tmp_path):
    # The shared in-memory SQLite connection cannot demonstrate writer isolation.
    # Preserve the opt-in disposable PostgreSQL URL for the same tests there.
    if settings.database_url.startswith("sqlite"):
        return settings.model_copy(
            update={"database_url": f"sqlite+aiosqlite:///{tmp_path / 'asset-race.db'}"}
        )
    return settings


def synchronise_admission(monkeypatch):
    """Make both independent requests reach the lock before either acquires it."""
    original = SqlUserRepository.lock_administration
    ready = asyncio.Event()
    arrivals = 0

    async def lock(repository):
        nonlocal arrivals
        arrivals += 1
        if arrivals >= 2:
            ready.set()
        await ready.wait()
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)


@pytest.mark.parametrize(
    ("limit", "maximum", "rejection"),
    [
        ("MAX_PENDING_UPLOADS", 1, 429),
        ("MAX_PERSONAL_RECORDS", 1, 422),
        ("MAX_PERSONAL_BYTES", len(ORIGINAL), 422),
        ("MAX_TEAM_RECORDS", 1, 422),
        ("MAX_TEAM_BYTES", len(ORIGINAL), 422),
        ("MAX_GLOBAL_RECORDS", 1, 422),
        ("MAX_GLOBAL_BYTES", len(ORIGINAL), 422),
    ],
)
async def test_concurrent_reservations_do_not_oversubscribe(
    client, container, admin, user, monkeypatch, limit, maximum, rejection
):
    team = await team_for(container, admin, user) if limit.startswith("MAX_TEAM") else None
    record, _ = await original_report(container, user, team.id if team else None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    monkeypatch.setattr(asset_service, limit, maximum)
    synchronise_admission(monkeypatch)
    async with asyncio.timeout(30):
        responses = await asyncio.gather(
            *(
                client.post(asset_path(record), headers=headers, json=reserve_body())
                for _ in range(2)
            )
        )
    assert sorted(response.status_code for response in responses) == [201, rejection], [
        response.text for response in responses
    ]
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        assert await repository.usage() == (1, len(ORIGINAL))
        assert await repository.pending_count() == 1


async def test_concurrent_puts_consume_one_reservation_and_read_one_body(
    client, container, user, monkeypatch
):
    record, _ = await original_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    reservation = await client.post(asset_path(record), headers=headers, json=reserve_body())
    assert reservation.status_code == 201, reservation.text
    asset_id = reservation.json()["id"]
    synchronise_admission(monkeypatch)
    bodies_read = 0

    async def body():
        nonlocal bodies_read
        bodies_read += 1
        yield ORIGINAL

    async with asyncio.timeout(30):
        responses = await asyncio.gather(
            *(
                client.put(
                    f"{asset_path(record)}/{asset_id}/content",
                    headers={**headers, "Content-Type": "application/octet-stream"},
                    content=body(),
                )
                for _ in range(2)
            )
        )
    assert sorted(response.status_code for response in responses) == [200, 409], [
        response.text for response in responses
    ]
    assert bodies_read == 1
    async with container.session_factory() as session:
        repository = SqlOriginalAssetRepository(session)
        retained = await repository.content(UUID(asset_id))
        assert retained is not None and retained.content == ORIGINAL
        assert retained.asset.status == "active"
        assert await repository.usage() == (1, len(ORIGINAL))
        assert await repository.pending_count() == 0
