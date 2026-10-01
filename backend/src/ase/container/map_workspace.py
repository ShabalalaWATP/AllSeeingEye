"""Composition of the map document boundary."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.map_workspace import SqlMapWorkspaceRepository
from ase.application.map_workspace import MapWorkspace
from ase.application.map_workspace_links import MapWorkspaceLinks
from ase.container.core import ContainerCore

if TYPE_CHECKING:
    pass


class MapWorkspaceWiring(ContainerCore):
    def map_workspace(self, session: AsyncSession) -> MapWorkspace:
        repos = self.repositories(session)
        documents = SqlMapWorkspaceRepository(session)
        return MapWorkspace(
            repos.users,
            repos.refresh_tokens,
            documents,
            self.access_policy(session),
            self.clock,
            self._auditor(repos),
            repos.uow,
            MapWorkspaceLinks(repos.plans),
        )
