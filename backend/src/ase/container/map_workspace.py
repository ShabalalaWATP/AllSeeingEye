"""Composition of the map document boundary."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.map_workspace import SqlMapWorkspaceRepository
from ase.application.map_workspace import MapWorkspace

if TYPE_CHECKING:
    from ase.application.access import AccessPolicy
    from ase.application.auditing import Auditor
    from ase.application.ports import Clock
    from ase.container.repositories import Repositories


class MapWorkspaceWiring:
    if TYPE_CHECKING:
        clock: Clock

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...

    def map_workspace(self, session: AsyncSession) -> MapWorkspace:
        repos = self.repositories(session)
        return MapWorkspace(
            repos.users,
            repos.refresh_tokens,
            SqlMapWorkspaceRepository(session),
            self.access_policy(session),
            self.clock,
            self._auditor(repos),
            repos.uow,
        )
