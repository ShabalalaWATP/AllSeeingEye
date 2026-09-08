"""Fixed public camera catalogue sources."""

from typing import Protocol

from ase.domain.cameras import Camera, CameraProviderId


class CameraSource(Protocol):
    @property
    def id(self) -> CameraProviderId: ...

    @property
    def name(self) -> str: ...

    async def fetch(self) -> tuple[Camera, ...]: ...
