"""Only two fixed HTTPS destinations; no caller-supplied symbols, URLs or pagination."""

from ase.adapters.economy.ecb import ECB_URL, parse_ecb
from ase.adapters.economy.world_bank import parse_world_bank, world_bank_url
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports.services import Clock
from ase.domain.economy import EconomyRegion, EconomySeries


class PublicEconomyGateway:
    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    async def macro(self) -> tuple[EconomyRegion, ...]:
        now = self._clock.now()
        try:
            payload = await self._http.get_json(
                world_bank_url(now), conditional=False, max_redirects=0
            )
            return parse_world_bank(payload, now)
        except (FeedFetchError, NotModified, TypeError, KeyError, OverflowError):
            raise ValueError("Economic indicators are temporarily unavailable") from None

    async def fx(self) -> tuple[EconomySeries, ...]:
        try:
            payload = await self._http.get_bytes(ECB_URL, conditional=False, max_redirects=0)
            return parse_ecb(payload, self._clock.now())
        except (FeedFetchError, NotModified, TypeError, KeyError, OverflowError):
            raise ValueError("Exchange rates are temporarily unavailable") from None
