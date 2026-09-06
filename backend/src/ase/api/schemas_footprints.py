"""Typed GeoJSON footprint response with deliberately restricted catalogue metadata."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from ase.domain.footprints import FootprintCollection, FootprintQuery


class FootprintSearchIn(BaseModel):
    bbox: tuple[float, float, float, float]
    since: datetime
    until: datetime
    disclose_to_provider: Literal[True]

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        self.to_query()
        return self

    def to_query(self) -> FootprintQuery:
        return FootprintQuery(self.bbox, self.since, self.until, self.disclose_to_provider)


class FootprintGeometryOut(BaseModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[tuple[float, float]]]]


class FootprintPropertiesOut(BaseModel):
    collection: str
    captured_at: datetime
    cloud_cover: float | None
    source_url: str
    licence: str
    licence_url: str


class FootprintFeatureOut(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: FootprintGeometryOut
    properties: FootprintPropertiesOut


class FootprintCollectionOut(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    status: Literal["completed", "empty", "unavailable"]
    features: list[FootprintFeatureOut] = Field(max_length=20)
    truncated: bool
    limitations: str
    queried_at: datetime

    @classmethod
    def from_domain(cls, result: FootprintCollection) -> Self:
        return cls(
            status=result.status,
            truncated=result.truncated,
            limitations=result.limitations,
            queried_at=result.queried_at,
            features=[
                FootprintFeatureOut(
                    id=feature.id,
                    geometry=FootprintGeometryOut(
                        coordinates=[
                            [list(ring) for ring in polygon] for polygon in feature.polygons
                        ]
                    ),
                    properties=FootprintPropertiesOut(
                        collection=feature.collection,
                        captured_at=feature.captured_at,
                        cloud_cover=feature.cloud_cover,
                        source_url=feature.source_url,
                        licence=feature.licence,
                        licence_url=feature.licence_url,
                    ),
                )
                for feature in result.features
            ],
        )
