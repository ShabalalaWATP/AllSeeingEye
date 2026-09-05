"""Geography ports: turning coordinates into countries."""

from __future__ import annotations

from typing import Protocol


class CountryResolver(Protocol):
    def resolve(self, lon: float, lat: float) -> str | None:
        """ISO 3166-1 alpha-2 code of the country containing the point, or None at sea."""
        ...
