"""Response models for geography endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ase.adapters.geo.countries import Country


class CountryOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    iso2: str
    iso3: str
    name: str
    bounds: tuple[float, float, float, float]
    centroid: tuple[float, float]

    @classmethod
    def from_country(cls, country: Country) -> CountryOut:
        return cls(
            iso2=country.iso2,
            iso3=country.iso3,
            name=country.name,
            bounds=country.bounds,
            centroid=country.centroid,
        )


class CountriesOut(BaseModel):
    items: list[CountryOut]


class CapabilitiesOut(BaseModel):
    """What this deployment can offer the browser beyond the always-on features."""

    os_maps: bool
    os_layers: list[str]
