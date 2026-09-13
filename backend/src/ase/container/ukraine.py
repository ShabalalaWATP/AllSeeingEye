"""Ukraine war tracker: packaged snapshots plus the shared live store, no per-request network."""

from functools import cached_property
from typing import TYPE_CHECKING, cast

from ase.adapters.geo.ukraine import load_control_snapshot, load_oblast_outlines
from ase.application.ukraine import UkraineBoardService
from ase.domain.ukraine.control import ControlSnapshot, NamedOutline

if TYPE_CHECKING:
    from ase.container import Container


class UkraineWiring:
    @cached_property
    def ukraine_control(self) -> ControlSnapshot | None:
        return load_control_snapshot()

    @cached_property
    def ukraine_outlines(self) -> tuple[NamedOutline, ...]:
        return load_oblast_outlines()

    def ukraine(self) -> UkraineBoardService:
        container = cast("Container", self)
        return UkraineBoardService(
            container.store, container.clock, container.conflicts, self.ukraine_control
        )
