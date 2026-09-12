"""Two independent bounded caches; concurrent readers share one refresh per provider."""

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from ase.application.ports.economy import EconomyGateway
from ase.application.ports.services import Clock
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.economy import EconomySeries, EconomySnapshot
from ase.domain.economy_catalogue import empty_fx, empty_regions

FAILURE_COOLDOWN = timedelta(minutes=5)
PROVIDER_TIMEOUT = 18


@dataclass
class _Cache:
    ttl: timedelta
    max_stale: timedelta
    refreshed_at: datetime | None = None
    retry_at: datetime | None = None
    failed: bool = False
    task: asyncio.Task[None] | None = None


class EconomyService:
    def __init__(
        self, gateway: EconomyGateway, clock: Clock, *, admission: SourceAdmission | None = None
    ) -> None:
        self._gateway, self._clock = gateway, clock
        self._admission = admission
        self._macro = _Cache(timedelta(hours=24), timedelta(days=7))
        self._fx = _Cache(timedelta(hours=1), timedelta(days=3))
        self._regions, self._rates = empty_regions(), empty_fx()

    async def snapshot(self) -> EconomySnapshot:
        enabled = await self._enabled()
        await asyncio.gather(
            *(
                self._ensure(cache)
                for key, cache in (("research-world-bank", self._macro), ("economic-ecb", self._fx))
                if enabled[key]
            )
        )
        now = self._clock.now()
        retries = [
            cache.retry_at
            for cache in (self._macro, self._fx)
            if cache.retry_at and cache.retry_at > now
        ]
        snapshot = EconomySnapshot(
            now,
            min(retries) if retries else now + FAILURE_COOLDOWN,
            tuple(
                replace(region, series=tuple(self._visible(s, self._macro) for s in region.series))
                for region in self._regions
            ),
            tuple(self._visible(s, self._fx) for s in self._rates),
        )
        return await self.refilter(snapshot)

    async def refilter(self, snapshot: EconomySnapshot) -> EconomySnapshot:
        """Recheck source visibility only. The final releaser holds the source guard."""
        enabled = await self._enabled()
        return replace(
            snapshot,
            regions=snapshot.regions
            if enabled["research-world-bank"]
            else tuple(
                replace(region, series=tuple(_disabled(item) for item in region.series))
                for region in empty_regions()
            ),
            fx=snapshot.fx
            if enabled["economic-ecb"]
            else tuple(
                _disabled(item) if item.id in {"GBP", "USD", "CNY"} else item for item in empty_fx()
            ),
        )

    async def _enabled(self) -> dict[str, bool]:
        keys = ("research-world-bank", "economic-ecb")
        return (
            await self._admission.enabled_many(keys)
            if self._admission
            else dict.fromkeys(keys, True)
        )

    async def _ensure(self, cache: _Cache) -> None:
        if cache.retry_at and self._clock.now() < cache.retry_at:
            return
        if cache.task is None or cache.task.done():
            cache.task = asyncio.create_task(self._refresh(cache))
        # Cancelling a browser request must not cancel the shared provider refresh.
        await asyncio.shield(cache.task)

    async def _refresh(self, cache: _Cache) -> None:
        try:
            async with asyncio.timeout(PROVIDER_TIMEOUT):
                if cache is self._macro:
                    self._regions = await self._gateway.macro()
                else:
                    self._rates = await self._gateway.fx()
            cache.failed = False
            cache.refreshed_at = self._clock.now()
            cache.retry_at = cache.refreshed_at + cache.ttl
        except (OSError, ValueError, TimeoutError):
            cache.failed = True
            cache.retry_at = self._clock.now() + FAILURE_COOLDOWN

    def _visible(self, series: EconomySeries, cache: _Cache) -> EconomySeries:
        if not cache.failed or series.status == "unavailable":
            return series
        retained = cache.refreshed_at and self._clock.now() - cache.refreshed_at <= cache.max_stale
        return replace(
            series,
            status="stale" if retained else "unavailable",
            points=series.points if retained else (),
            note=series.note
            + (
                " The latest refresh failed; these are previously fetched observations."
                if retained
                else " Previously fetched observations expired while the provider was unavailable."
            ),
        )

    async def aclose(self) -> None:
        tasks = [cache.task for cache in (self._macro, self._fx) if cache.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _disabled(series: EconomySeries) -> EconomySeries:
    return replace(series, note="This source is disabled by the administrator. No data is shown.")
