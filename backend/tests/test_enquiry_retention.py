"""Fixed-clock retention is bounded, immediate for reads, and safe to repeat."""

import asyncio
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from structlog.testing import capture_logs

from ase.adapters.persistence.enterprise_enquiries import EnterpriseEnquiryRow
from ase.container.enquiry_retention import PURGE_BATCH_SIZE, purge_enquiries
from ase.container.original_asset_expiry import expire_original_assets
from ase.infrastructure.settings import Settings
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_admin_enquiries import seed


async def test_retention_purges_one_bounded_batch_and_preserves_boundary(container, clock):
    for _ in range(PURGE_BATCH_SIZE + 1):
        await seed(container, days=366)
    boundary = await seed(container, days=365)
    retained = await seed(container)
    async with container.session_factory() as session:
        await container.repositories(session).users.lock_administration()
        assert await purge_enquiries(session, clock, 365) == PURGE_BATCH_SIZE
        await session.commit()
        assert await purge_enquiries(session, clock, 365) == 1
        await session.commit()
        assert await purge_enquiries(session, clock, 365) == 0
        assert await session.get(EnterpriseEnquiryRow, boundary.id) is not None
        assert await session.get(EnterpriseEnquiryRow, retained.id) is not None
        assert await session.scalar(select(func.count()).select_from(EnterpriseEnquiryRow)) == 2
    clock.advance(timedelta(microseconds=1))
    async with container.session_factory() as session:
        assert await purge_enquiries(session, clock, 365) == 1
        await session.rollback()
        assert await session.get(EnterpriseEnquiryRow, boundary.id) is not None


async def test_retention_applies_when_submission_disabled(client, container, admin):
    item = await seed(container, days=31)
    container.settings = container.settings.model_copy(
        update={"enterprise_enquiry_retention_days": 30}
    )
    assert not container.settings.enterprise_enquiries_enabled
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    assert (await client.get(f"/api/admin/enquiries/{item.id}", headers=headers)).status_code == 404
    assert (await client.get("/api/admin/enquiries", headers=headers)).json()["total"] == 0
    async with container.session_factory() as session:
        assert await purge_enquiries(session, container.clock, 30) == 1
    assert (await client.get("/api/site")).json()["enterprise_enquiry_retention_days"] == 30


async def test_housekeeping_commits_purge_and_logs_only_count(container, clock, monkeypatch):
    item = await seed(container, days=31)

    async def one_cycle(name, interval, callback):
        await callback()
        raise asyncio.CancelledError

    monkeypatch.setattr("ase.container.original_asset_expiry.run_cycle", one_cycle)
    with capture_logs() as records, pytest.raises(asyncio.CancelledError):
        await expire_original_assets(container.session_factory, clock, 30)
    assert [row for row in records if row["event"] == "enquiries.expired"] == [
        {"event": "enquiries.expired", "count": 1, "log_level": "info"},
    ]
    async with container.session_factory() as session:
        assert await session.get(EnterpriseEnquiryRow, item.id) is None


def test_retention_settings_have_documented_safe_bounds():
    assert Settings(_env_file=None).enterprise_enquiry_retention_days == 365
    assert (
        Settings(
            _env_file=None, enterprise_enquiry_retention_days=30
        ).enterprise_enquiry_retention_days
        == 30
    )
    for value in (29, 3651):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, enterprise_enquiry_retention_days=value)
