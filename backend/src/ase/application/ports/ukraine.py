"""Runtime providers for the Ukraine page: frontline geometry and spotted losses."""

from __future__ import annotations

from typing import Protocol

from ase.domain.ukraine.frontline import FrontlineState, SpottedState


class FrontlineSource(Protocol):
    async def snapshot(self) -> FrontlineState: ...
    async def spotted(self) -> SpottedState: ...
