"""Public camera facilities and explicit catalogue health."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.domain.cameras import CameraProviderId


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    provider: CameraProviderId
    title: str
    latitude: float
    longitude: float
    snapshot_url: str | None
    source_url: str
    attribution: str
    captured_at: datetime | None
    stream_url: str | None = None
    stream_type: Literal["hls", "mp4", "mjpeg", "iframe"] | None = None
    external_url: str | None = None
    coordinate_precision: Literal["exact", "approximate"] = "exact"


class CameraProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: CameraProviderId
    name: str
    status: Literal["available", "stale", "unavailable", "not_loaded"]
    count: int
    fetched_at: datetime | None
    message: str | None


class CameraCatalogueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cameras: list[CameraOut]
    providers: list[CameraProviderOut]
    fetched_at: datetime
