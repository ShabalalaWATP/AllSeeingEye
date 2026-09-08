"""Public transport camera facilities, separate from transient reported events."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CameraProviderId = Literal["tfl", "hongkong", "fintraffic"]


@dataclass(frozen=True, slots=True)
class Camera:
    id: str
    provider: CameraProviderId
    title: str
    latitude: float
    longitude: float
    snapshot_url: str
    source_url: str
    attribution: str
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CameraProviderStatus:
    id: CameraProviderId
    name: str
    status: Literal["available", "stale", "unavailable"]
    count: int
    fetched_at: datetime | None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class CameraCatalogue:
    cameras: tuple[Camera, ...]
    providers: tuple[CameraProviderStatus, ...]
    fetched_at: datetime
