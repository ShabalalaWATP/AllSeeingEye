"""Port for preserving cited URLs so a report stays verifiable after the live store moves on."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Archiver(Protocol):
    async def archive(self, url: str, published_at: datetime) -> str | None:
        """The address of a snapshot taken since publication, or None when none can be had."""
        ...

    async def aclose(self) -> None: ...
