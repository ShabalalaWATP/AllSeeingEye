"""Session-scoped team use cases for authorisation tests."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.teams.service import TeamService
from ase.container import Container

CONTEXT = RequestContext(ip="127.0.0.1", user_agent=None)


@asynccontextmanager
async def team_service(container: Container) -> AsyncIterator[TeamService]:
    async with container.session_factory() as session:
        repos = container.repositories(session)
        yield TeamService(
            SqlTeamRepository(session),
            repos.users,
            container.clock,
            Auditor(repos.audit, container.clock),
            repos.uow,
        )
