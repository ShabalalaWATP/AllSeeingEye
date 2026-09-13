"""Public figures: packaged roster plus the shared live store, no per-request network."""

from functools import cached_property
from typing import TYPE_CHECKING, cast

from ase.adapters.geo.public_figures import load_public_figures
from ase.application.public_figures import PublicFigureService
from ase.domain.public_figures import PublicFigureCatalogue

if TYPE_CHECKING:
    from ase.container import Container


class PublicFigureWiring:
    @cached_property
    def figure_catalogue(self) -> PublicFigureCatalogue:
        return load_public_figures()

    def public_figures(self) -> PublicFigureService:
        container = cast("Container", self)
        return PublicFigureService(container.store, container.clock, self.figure_catalogue)
