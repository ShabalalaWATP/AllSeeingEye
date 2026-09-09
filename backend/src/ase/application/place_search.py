"""Explicit transient place searches with shared, fail-fast provider admission."""

import asyncio
from uuid import UUID

from ase.application.ports.navigation import PlaceSearchGateway
from ase.application.ports.services import RateLimiter
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.navigation import NavigationPlace


class PlaceSearch:
    def __init__(self, gateway: PlaceSearchGateway, limiter: RateLimiter) -> None:
        self._gateway, self._limiter = gateway, limiter
        self._busy = False

    async def search(self, actor_id: UUID, query: str) -> tuple[NavigationPlace, ...]:
        query = query.strip()
        if not 3 <= len(query) <= 200 or any(ord(char) < 32 for char in query):
            raise InvalidRequest("Enter an address or place name between 3 and 200 characters.")
        retry = self._limiter.hit(f"place-search:{actor_id}", 12, 60)
        if retry is not None:
            raise RateLimited(retry)
        if self._busy:
            raise RateLimited(1)
        retry = self._limiter.hit("place-search:provider", 1, 1)
        if retry is not None:
            raise RateLimited(retry)
        self._busy = True
        try:
            async with asyncio.timeout(10):
                return await self._gateway.search(query)
        except Exception:
            raise InvalidRequest(
                "Address search unavailable. Try again later or use coordinates."
            ) from None
        finally:
            self._busy = False
