"""Pipeline stage that attributes located events to a country."""

from __future__ import annotations

from ase.application.ports.geo import CountryResolver
from ase.domain.events import Event


class CountryStage:
    """Fills `country_iso` from coordinates for events that arrived without one."""

    def __init__(self, resolver: CountryResolver) -> None:
        self._resolver = resolver

    def process(self, events: list[Event]) -> list[Event]:
        result: list[Event] = []
        for event in events:
            if event.country_iso is not None or event.point is None:
                result.append(event)
                continue
            iso = self._resolver.resolve(event.point.lon, event.point.lat)
            result.append(event if iso is None else event.with_changes(country_iso=iso))
        return result
