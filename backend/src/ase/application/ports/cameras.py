"""Fixed public camera catalogue sources."""

from typing import Protocol

from ase.domain.cameras import Camera, CameraProviderId


class CameraSource(Protocol):
    @property
    def id(self) -> CameraProviderId: ...

    @property
    def name(self) -> str: ...

    async def fetch(self) -> tuple[Camera, ...]: ...


class CameraFrameSource(CameraSource, Protocol):
    """A source whose provider serves images only inline, so the server relays one frame."""

    async def frame(self, frame_id: str) -> bytes | None: ...
