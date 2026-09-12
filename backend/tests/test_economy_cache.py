"""Provider independence, bounded caching, admission changes and request cancellation."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.application import economy
from ase.application.economy import EconomyService
from helpers import FakeClock
from test_economy_data import NOW, fx_payload, parse_ecb, parse_world_bank, wb_payload


def gateway():
    return AsyncMock(
        macro=AsyncMock(return_value=parse_world_bank(wb_payload(), NOW)),
        fx=AsyncMock(return_value=parse_ecb(fx_payload(), NOW)),
    )


async def test_parallel_visitors_share_refresh_and_provider_ttls_are_independent():
    source, clock = gateway(), FakeClock(NOW)
    service = EconomyService(source, clock)
    snapshots = await asyncio.gather(*(service.snapshot() for _ in range(20)))
    assert len(snapshots) == 20
    assert source.macro.await_count == source.fx.await_count == 1
    assert snapshots[0].refresh_after == NOW + timedelta(hours=1)
    clock.advance(timedelta(hours=1))
    await service.snapshot()
    assert source.macro.await_count == 1 and source.fx.await_count == 2
    clock.advance(timedelta(hours=23))
    await service.snapshot()
    assert source.macro.await_count == 2 and source.fx.await_count == 3
    await service.aclose()


async def test_independent_failures_retain_labelled_data_then_expire():
    source, clock = gateway(), FakeClock(NOW)
    service = EconomyService(source, clock)
    await service.snapshot()
    source.fx.side_effect = ValueError("not surfaced")
    clock.advance(timedelta(hours=1))
    result = await service.snapshot()
    assert result.fx[0].status == "stale" and result.fx[0].updated_at == NOW
    assert result.regions[1].series[0].status == "available"
    assert "not surfaced" not in result.fx[0].note
    assert result.refresh_after == clock.now() + timedelta(minutes=5)
    await service.snapshot()
    assert source.fx.await_count == 2
    clock.advance(timedelta(days=4))
    result = await service.snapshot()
    assert result.fx[0].status == "unavailable" and result.fx[0].points == ()
    assert result.regions[1].series[0].status == "available"


async def test_first_failure_and_timeout_return_explicit_gaps(monkeypatch):
    source = gateway()
    source.macro.side_effect = ValueError("failed")
    never = asyncio.Event()

    async def wait():
        await never.wait()

    source.fx.side_effect = wait
    monkeypatch.setattr(economy, "PROVIDER_TIMEOUT", 0.001)
    service = EconomyService(source, FakeClock(NOW))
    result = await service.snapshot()
    assert all(item.status == "unavailable" for region in result.regions for item in region.series)
    assert all(item.status == "unavailable" for item in result.fx)
    assert result.refresh_after == NOW + timedelta(minutes=5)


async def test_cancelled_browser_does_not_cancel_shared_provider_work():
    source, entered, release = gateway(), asyncio.Event(), asyncio.Event()

    async def wait():
        entered.set()
        await release.wait()
        return parse_world_bank(wb_payload(), NOW)

    source.macro.side_effect = wait
    service = EconomyService(source, FakeClock(NOW))
    first = asyncio.create_task(service.snapshot())
    await entered.wait()
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    second = asyncio.create_task(service.snapshot())
    release.set()
    assert (await second).regions[1].series[0].status == "available"
    assert source.macro.await_count == 1
    await service.aclose()


async def test_source_disable_blocks_fetch_and_hides_cached_results_after_network():
    source = gateway()
    admission = AsyncMock()
    admission.enabled_many.return_value = {"research-world-bank": False, "economic-ecb": True}
    service = EconomyService(source, FakeClock(NOW), admission=admission)
    result = await service.snapshot()
    source.macro.assert_not_awaited()
    assert result.regions[1].series[0].status == "unavailable"
    admission.enabled_many.side_effect = [
        {"research-world-bank": True, "economic-ecb": True},
        {"research-world-bank": False, "economic-ecb": False},
    ]
    result = await service.snapshot()
    assert source.macro.await_count == 1
    assert result.regions[1].series[0].points == () and result.fx[0].points == ()
