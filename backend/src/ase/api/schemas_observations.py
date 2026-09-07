"""Frozen source geometry and observation metadata for evidence inspection."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole, geometry_to_dict


class SourceGeometryOut(BaseModel):
    type: Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    coordinates: list[JsonValue]


class EvidenceGeometryOut(BaseModel):
    geometry: SourceGeometryOut
    sha256: str
    location_role: LocationRole
    precision: str
    method: str
    source_id: str
    attribution: str

    @model_validator(mode="before")
    @classmethod
    def from_domain(cls, value: Any) -> Any:
        # Domain construction already enforces WGS84 structure and byte/vertex bounds.
        return geometry_to_dict(value) if isinstance(value, EvidenceGeometry) else value


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    acquired_at: datetime
    processed_at: datetime | None
    collection_id: str
    item_id: str
    limitations: str
    scene_cloud_cover: float | None
