"""Admit bounded aircraft collection interests from authenticated map queries."""

from typing import Protocol
from uuid import UUID

from ase.application.ports.feeds import EventQuery
from ase.application.ports.services import RateLimiter
from ase.domain.events import Category


class AircraftInterests(Protocol):
    def request(self, latitude: float, longitude: float) -> None: ...


class MapCollectionInterests:
    def __init__(self, interests: AircraftInterests, limiter: RateLimiter) -> None:
        self._interests, self._limiter = interests, limiter

    def request(self, user_id: UUID, query: EventQuery) -> None:
        bounds = query.bbox
        if bounds is None or query.sampling != "geographic":
            return
        if query.categories and Category.AVIATION not in query.categories:
            return
        # The global sweep handles a whole-world view. Modulo arithmetic would
        # otherwise turn its 360-degree span into a point on the antimeridian.
        if bounds.east - bounds.west == 360:
            return
        # Optional collection must never prevent reading already retained data.
        if self._limiter.hit(f"map-aircraft:{user_id}", 60, 60) is not None:
            return
        width = (bounds.east - bounds.west) % 360
        longitude = (bounds.west + width / 2 + 180) % 360 - 180
        self._interests.request((bounds.south + bounds.north) / 2, longitude)
