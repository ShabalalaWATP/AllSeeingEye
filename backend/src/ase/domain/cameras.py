"""Public transport camera facilities, separate from transient reported events."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CameraProviderId = str


@dataclass(frozen=True, slots=True)
class Camera:
    id: str
    provider: CameraProviderId
    title: str
    latitude: float
    longitude: float
    snapshot_url: str | None
    source_url: str
    attribution: str
    captured_at: datetime | None = None
    stream_url: str | None = None
    stream_type: Literal["hls", "mp4", "mjpeg", "iframe"] | None = None
    external_url: str | None = None
    coordinate_precision: Literal["exact", "approximate"] = "exact"


@dataclass(frozen=True, slots=True)
class CameraProviderStatus:
    id: CameraProviderId
    name: str
    status: Literal["available", "stale", "unavailable", "not_loaded"]
    count: int
    fetched_at: datetime | None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class CameraCatalogue:
    cameras: tuple[Camera, ...]
    providers: tuple[CameraProviderStatus, ...]
    fetched_at: datetime
