"""Fixed public camera catalogue sources."""

from typing import Protocol

from ase.domain.cameras import Camera, CameraProviderId


class CameraSource(Protocol):
    id: CameraProviderId
    name: str

    async def fetch(self) -> tuple[Camera, ...]: ...
