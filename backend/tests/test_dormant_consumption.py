"""Dormant warning rules retain inclusive eligibility and corrupt fail-closed state."""

from datetime import timedelta
from uuid import UUID

import pytest

from ase.adapters.persistence.warning_consumption import load, prune_batch
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.container.dormant_retention import DormantRetention
from ase.domain.consumed_evidence import CONSUMED_RETENTION, encode, instant
from dormant_retention_helpers import seed
from test_consumed_alert_evidence import create_rule


async def test_mixed_expiry_and_legacy_boundary_preserve_replay_protection(container, user, clock):
    rule = await create_rule(container, user)
    now = clock.now()
    old, boundary = b"a" * 16, b"b" * 16
    await seed(
        container,
        WarningConsumptionRow(
            indicator_id=rule.id,
            data=encode({old: instant(now) - 1, boundary: instant(now)}),
            count=2,
            expires_at=now - timedelta(microseconds=1),
            legacy_before=now - CONSUMED_RETENTION,
        ),
    )
    maintenance = DormantRetention(container)
    await maintenance.consumed()
    async with container.session_factory() as session:
        retained = await load(session, rule.id, now)
        assert retained.identities == {boundary}
        assert retained.legacy_before == now - CONSUMED_RETENTION
    clock.advance(timedelta(microseconds=1))
    await maintenance.consumed()
    async with container.session_factory() as session:
        assert await session.get(WarningConsumptionRow, rule.id) is None


async def test_corrupt_first_record_does_not_starve_later_expired_rules(container, user, caplog):
    from ase.adapters.persistence.operational_models import IndicatorRow  # noqa: PLC0415

    first = await create_rule(container, user)
    second = await create_rule(container, user)
    # Use known ordered UUIDs to exercise a batch boundary deterministically.
    async with container.session_factory() as session:
        a, b = await session.get(IndicatorRow, first.id), await session.get(IndicatorRow, second.id)
        a.id, b.id = UUID(int=1), UUID(int=2)
        await session.commit()
    now = container.clock.now()
    await seed(
        container,
        WarningConsumptionRow(
            indicator_id=UUID(int=1), data=b"corrupt", count=1, expires_at=now - timedelta(days=1)
        ),
        WarningConsumptionRow(
            indicator_id=UUID(int=2),
            data=encode({}),
            count=0,
            legacy_before=now - CONSUMED_RETENTION - timedelta(seconds=1),
        ),
    )
    async with container.session_factory() as session:
        after, through, changed = await prune_batch(session, now, limit=1)
        assert (after, through, changed) == (UUID(int=1), UUID(int=2), 0)
        await session.commit()
    async with container.session_factory() as session:
        assert await prune_batch(session, now, after=after, through=through, limit=1) == (
            None,
            None,
            1,
        )
        await session.commit()
    async with container.session_factory() as session:
        assert (await load(session, UUID(int=1), now)).unavailable == "invalid_consumed_evidence"
        assert await session.get(WarningConsumptionRow, UUID(int=2)) is None


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_consumption_batch_is_rejected(container, limit):
    async with container.session_factory() as session:
        with pytest.raises(ValueError):
            await prune_batch(session, container.clock.now(), limit=limit)
