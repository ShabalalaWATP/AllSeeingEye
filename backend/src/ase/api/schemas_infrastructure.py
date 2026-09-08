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


class InfrastructureOut(BaseModel):
    cables: list[CableOut] = Field(max_length=3000)
    ground_stations: list[GroundStationOut] = Field(max_length=100)
    snapshot_date: str
    cable_attribution: str
    cable_licence_url: str
