"""Public figures: packaged roster plus the shared live store, no per-request network."""

from functools import cached_property

from ase.adapters.geo.public_figures import load_public_figures
from ase.application.public_figures import PublicFigureService
from ase.container.core import ContainerCore
from ase.domain.public_figures import PublicFigureCatalogue


class PublicFigureWiring(ContainerCore):
    @cached_property
    def figure_catalogue(self) -> PublicFigureCatalogue:
        return load_public_figures()

    def public_figures(self) -> PublicFigureService:
        return PublicFigureService(
            self.store, self.clock, self.figure_catalogue, licences=self.source_licences
        )
