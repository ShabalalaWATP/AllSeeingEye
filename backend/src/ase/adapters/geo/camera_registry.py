"""Explicit source registry. No operator-supplied endpoints or executable adapters."""

from dataclasses import dataclass

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo import camera_americas, camera_europe, camera_world, camera_world_directory
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


def build_sources(http: CameraHttpClient, digitraffic: FeedHttpClient) -> tuple[CameraSource, ...]:
    sources = (
        OfficialCameraSource("tfl", http),
        OfficialCameraSource("hongkong", http),
        OfficialCameraSource("fintraffic", digitraffic),
        *camera_americas.build_sources(http),
        *camera_europe.build_sources(http),
        *camera_world.build_sources(http),
        *camera_world_directory.build_sources(http),
    )
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("Duplicate camera provider IDs")
    return tuple(GuardedCameraSource(source) for source in sources)
