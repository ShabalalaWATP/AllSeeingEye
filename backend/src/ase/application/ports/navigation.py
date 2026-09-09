"""Fixed-provider route calculation without persistent location history."""

from typing import Protocol

from ase.domain.events import Point
from ase.domain.navigation import NavigationPlace, NavigationRoute, RouteMode


class RoutingGateway(Protocol):
    async def route(self, mode: RouteMode, waypoints: tuple[Point, ...]) -> NavigationRoute: ...


class PlaceSearchGateway(Protocol):
    async def search(self, query: str) -> tuple[NavigationPlace, ...]: ...
