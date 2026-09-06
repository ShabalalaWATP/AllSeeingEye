"""Pipeline stage that attributes located events to a country."""

from __future__ import annotations

from ase.application.ports.geo import CountryDirectory, CountryResolver
from ase.domain.events import Event


class CountryStage:
    """Resolve supplied coordinates, never invent a point from a country reference."""

    def __init__(
        self, resolver: CountryResolver, directory: CountryDirectory | None = None
    ) -> None:
        self._resolver = resolver
        # Retain the optional constructor argument for existing composition callers.
        # Country centroids are navigation references, not event observations.

    def process(self, events: list[Event]) -> list[Event]:
        result: list[Event] = []
        for event in events:
            if event.point is None:
                result.append(event)
                continue
            if event.country_iso is not None:
                result.append(event)
                continue
            iso = self._resolver.resolve(event.point.lon, event.point.lat)
            result.append(event if iso is None else event.with_changes(country_iso=iso))
        return result
