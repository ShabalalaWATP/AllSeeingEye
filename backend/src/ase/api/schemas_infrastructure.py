"""Read-only public infrastructure map contract."""

from pydantic import BaseModel, Field


class CableOut(BaseModel):
    id: str
    name: str
    category: str
    path: list[tuple[float, float]] = Field(max_length=512)
    source_url: str
    note: str


class GroundStationOut(BaseModel):
    id: str
    name: str
    operator: str
    country: str
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    source_url: str
    note: str
    website: str | None = None
    wikipedia: str | None = None


class DataCentreOut(BaseModel):
    id: str
    name: str
    operator: str
    country: str | None = Field(default=None, min_length=2, max_length=2)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    website: str | None = None
    source_url: str
    note: str


class NuclearFacilityOut(BaseModel):
    id: str
    name: str
    country: str
    country_code: str = Field(pattern=r"^[A-Z]{3}$")
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    capacity_mw: float | None = Field(ge=0, le=100_000)
    capacity_year: int | None = Field(ge=1900, le=2099)
    operator: str | None
    source_name: str
    source_url: str
    geolocation_source: str
    note: str


class InfrastructureOut(BaseModel):
    cables: list[CableOut] = Field(max_length=3000)
    ground_stations: list[GroundStationOut] = Field(max_length=500)
    data_centres: list[DataCentreOut] = Field(max_length=4000)
    data_centre_attribution: str
    data_centre_licence_url: str
    data_centre_snapshot_date: str
    snapshot_date: str
    cable_attribution: str
    cable_licence_url: str
    nuclear_facilities: list[NuclearFacilityOut] = Field(max_length=1000)
    nuclear_attribution: str
    nuclear_licence_url: str
    nuclear_dataset_version: str
    nuclear_snapshot_date: str
