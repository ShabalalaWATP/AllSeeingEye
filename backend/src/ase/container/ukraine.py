"""Ukraine war tracker: packaged snapshots plus the shared live store, no per-request network."""

from functools import cached_property
from typing import TYPE_CHECKING, cast

from ase.adapters.feeds.ukraine_frontline import FrontlineProviders
from ase.adapters.geo.ukraine import load_control_snapshot, load_oblast_outlines
from ase.adapters.geo.ukraine_figures import load_civilian_harm, load_confirmed_losses
from ase.adapters.geo.ukraine_reference import load_reference_catalogue, load_reference_image
from ase.application.ukraine import UkraineBoardService
from ase.domain.ukraine.confirmed import CivilianHarm, ConfirmedLosses
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

    @cached_property
    def ukraine_confirmed(self) -> ConfirmedLosses | None:
        return load_confirmed_losses()

    @cached_property
    def ukraine_civilian_harm(self) -> CivilianHarm | None:
        return load_civilian_harm()

    @cached_property
    def ukraine_providers(self) -> FrontlineProviders:
        container = cast("Container", self)
        settings = container.settings
        return FrontlineProviders(
            container.http,
            container.clock,
            deepstate=settings.ukraine_deepstate_access == "granted",
            ocha=settings.ukraine_ocha_humanitarian,
            spotted=settings.ukraine_warspotting,
        )

    def ukraine(self) -> UkraineBoardService:
        container = cast("Container", self)
        return UkraineBoardService(
            container.store,
            container.clock,
            container.conflicts,
            self.ukraine_control,
            self.ukraine_confirmed,
            self.ukraine_civilian_harm,
        )
