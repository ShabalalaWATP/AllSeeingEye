"""Geography ports: turning coordinates into countries and listing the countries known."""

from __future__ import annotations

from typing import Protocol

from ase.domain.countries import Country


class CountryResolver(Protocol):
    def resolve(self, lon: float, lat: float) -> str | None:
        """ISO 3166-1 alpha-2 code of the country containing the point, or None at sea."""
        ...


class CountryDirectory(CountryResolver, Protocol):
    def get(self, iso2: str) -> Country | None: ...

    def countries(self) -> list[Country]:
        """Every known country, sorted by name."""
        ...
