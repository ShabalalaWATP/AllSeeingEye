"""Public economic data boundaries shared by the dashboard and report evidence."""

from typing import Protocol

from ase.domain.economy import EconomyRegion, EconomySeries, EconomySnapshot


class EconomyGateway(Protocol):
    async def macro(self) -> tuple[EconomyRegion, ...]: ...
    async def fx(self) -> tuple[EconomySeries, ...]: ...


class EconomyReader(Protocol):
    async def snapshot(self) -> EconomySnapshot: ...
