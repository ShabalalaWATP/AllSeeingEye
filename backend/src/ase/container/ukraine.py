"""Ukraine war tracker: packaged snapshots plus the shared live store, no per-request network."""

from functools import cached_property
from typing import TYPE_CHECKING, cast

from ase.adapters.geo.ukraine import load_control_snapshot, load_oblast_outlines
from ase.adapters.geo.ukraine_reference import load_reference_catalogue, load_reference_image
from ase.application.ukraine import UkraineBoardService
from ase.domain.ukraine.control import ControlSnapshot, NamedOutline
from ase.domain.ukraine.reference import ReferenceCatalogue

if TYPE_CHECKING:
    from ase.container import Container


class UkraineWiring:
    @cached_property
    def ukraine_control(self) -> ControlSnapshot | None:
        return load_control_snapshot()

    @cached_property
    def ukraine_outlines(self) -> tuple[NamedOutline, ...]:
        return load_oblast_outlines()

    @cached_property
    def ukraine_reference(self) -> ReferenceCatalogue | None:
        return load_reference_catalogue()

    def ukraine_image(self, image_id: str) -> bytes | None:
        return load_reference_image(image_id)

    def ukraine(self) -> UkraineBoardService:
        container = cast("Container", self)
        return UkraineBoardService(
            container.store, container.clock, container.conflicts, self.ukraine_control
        )
