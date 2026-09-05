"""Pipeline stage that attributes located events to a country."""

from __future__ import annotations

from ase.application.ports.geo import CountryDirectory, CountryResolver
from ase.domain.events import Event, GeoConfidence, Point


class CountryStage:
    """Fills `country_iso` from coordinates for events that arrived without one, and gives
    country-level events (a code but no coordinates) the nation's centroid to sit on."""

    def __init__(
        self, resolver: CountryResolver, directory: CountryDirectory | None = None
    ) -> None:
        self._resolver = resolver
        self._directory = directory

    def process(self, events: list[Event]) -> list[Event]:
        result: list[Event] = []
        for event in events:
            if event.point is None:
                result.append(self._place(event))
                continue
            if event.country_iso is not None:
                result.append(event)
                continue
            iso = self._resolver.resolve(event.point.lon, event.point.lat)
            result.append(event if iso is None else event.with_changes(country_iso=iso))
        return result

    def _place(self, event: Event) -> Event:
        if (
            self._directory is None
            or event.country_iso is None
            or event.geo_confidence is not GeoConfidence.COUNTRY
        ):
            return event
        country = self._directory.get(event.country_iso)
        if country is None:
            return event
        lon, lat = country.centroid
        return event.with_changes(point=Point(lon=lon, lat=lat))
