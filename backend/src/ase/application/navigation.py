"""Small explicit route requests with shared public-provider admission."""

import asyncio
from itertools import pairwise
from uuid import UUID

from ase.application.ports.navigation import RoutingGateway
from ase.application.ports.services import RateLimiter
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.event_similarity import distance_km
from ase.domain.events import Point
from ase.domain.navigation import NavigationRoute, RouteMode


class RoutePlanner:
    def __init__(self, gateway: RoutingGateway, limiter: RateLimiter) -> None:
        self._gateway, self._limiter = gateway, limiter
        self._busy = False

    async def calculate(
        self, actor_id: UUID, mode: RouteMode, waypoints: tuple[Point, ...]
    ) -> NavigationRoute:
        if mode not in {"driving", "walking", "cycling"} or not 2 <= len(waypoints) <= 8:
            raise InvalidRequest("Choose a supported travel mode and two to eight waypoints.")
        distance = sum(distance_km(a, b) for a, b in pairwise(waypoints))
        if distance <= 0 or distance > (100 if mode == "walking" else 1000):
            raise InvalidRequest("Waypoints exceed the supported route distance or are identical.")
        retry = self._limiter.hit(f"navigation:{actor_id}", 6, 60)
        if retry is not None:
            raise RateLimited(retry)
        # Shared singleton in the supported one-process deployment: no waiting
        # queue retaining private waypoints, and never concurrent provider calls.
        if self._busy:
            raise RateLimited(1)
        retry = self._limiter.hit("navigation:provider", 1, 1)
        if retry is not None:
            raise RateLimited(retry)
        self._busy = True
        try:
            async with asyncio.timeout(15):
                return await self._gateway.route(mode, waypoints)
        except Exception:
            raise InvalidRequest(
                "Route unavailable. Check the waypoints or try again later."
            ) from None
        finally:
            self._busy = False
