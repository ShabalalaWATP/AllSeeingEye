"""Explicit source registry. No operator-supplied endpoints or executable adapters."""

from dataclasses import dataclass

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo import (
    camera_americas,
    camera_britain,
    camera_east,
    camera_europe,
    camera_europe_maps,
    camera_europe_open,
    camera_world,
    camera_world_directory,
    camera_world_open,
)
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.cameras import OfficialCameraSource
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera


@dataclass
class GuardedCameraSource:
    source: CameraSource

    @property
    def id(self) -> str:
        return self.source.id

    @property
    def name(self) -> str:
        return self.source.name

    @property
    def warning(self) -> str | None:
        message = getattr(self.source, "warning", None)
        return message if isinstance(message, str) else None

    async def fetch(self) -> tuple[Camera, ...]:
        try:
            return await self.source.fetch()
        except Exception as exc:
            # Convert provider/network/parser failures at the adapter boundary.
            # Cancellation inherits BaseException and is deliberately not swallowed.
            raise ValueError("Public camera provider unavailable") from exc

    async def frame(self, frame_id: str) -> bytes | None:
        reader = getattr(self.source, "frame", None)
        if reader is None:
            return None
        try:
            data = await reader(frame_id)
        except Exception as exc:
            raise ValueError("Public camera frame unavailable") from exc
        return data if isinstance(data, bytes) else None


def build_sources(
    http: CameraHttpClient,
    digitraffic: FeedHttpClient,
    *,
    wsdot_access_code: str | None = None,
) -> tuple[CameraSource, ...]:
    sources = (
        OfficialCameraSource("tfl", http),
        OfficialCameraSource("hongkong", http),
        OfficialCameraSource("fintraffic", digitraffic),
        *camera_americas.build_sources(http, wsdot_access_code=wsdot_access_code),
        *camera_europe.build_sources(http),
        *camera_world.build_sources(http),
        *camera_world_directory.build_sources(http),
        *camera_britain.build_sources(http),
        *camera_east.build_sources(http),
        *camera_europe_open.build_sources(http),
        *camera_europe_maps.build_sources(http),
        *camera_world_open.build_sources(http),
    )
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("Duplicate camera provider IDs")
    return tuple(GuardedCameraSource(source) for source in sources)
