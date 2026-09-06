"""Personal/team warning fixtures with real account and membership policies."""

from dataclasses import dataclass
from uuid import UUID

import pytest

from ase.application.schedules.manage import ScheduleInput
from ase.application.warning.indicators import IndicatorInput
from ase.container import Container
from ase.domain.schedules import Schedule
from ase.domain.teams import MembershipRole, Team
from ase.domain.users import Role, User
from ase.domain.warning import Indicator
from helpers import USER_PASSWORD, create_user
from team_helpers import CONTEXT, team_service


@dataclass
class WarningActors:
    owner: User
    peer: User
    manager: User
    outsider: User
    team: Team
    other: Team


@pytest.fixture
async def warning_actors(container: Container, admin: User, user: User) -> WarningActors:
    peer = await create_user(container, email="peer@example.com", password=USER_PASSWORD)
    manager = await create_user(
        container, email="lead@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    outsider = await create_user(container, email="outside@example.com", password=USER_PASSWORD)
    async with team_service(container) as service:
        team = await service.create(admin, "Warning desk", CONTEXT)
        other = await service.create(admin, "Other desk", CONTEXT)
        for actor, role in (
            (user, MembershipRole.MEMBER),
            (peer, MembershipRole.MEMBER),
            (manager, MembershipRole.MANAGER),
        ):
            await service.set_member(admin, team.id, email=actor.email, role=role, context=CONTEXT)
        await service.set_member(
            admin, other.id, email=outsider.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        await service.set_member(
            admin, other.id, email=manager.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    return WarningActors(user, peer, manager, outsider, team, other)


async def create_indicator(
    container: Container,
    actor: User,
    team_id: UUID | None,
    name: str = "Scoped warning",
    report: str | None = None,
) -> Indicator:
    async with container.session_factory() as session:
        return await container.create_indicator(session).execute(
            actor,
            IndicatorInput(
                name=name,
                countries=("UA",),
                keywords=("Kharkiv",),
                window_minutes=10080,
                report_template=report,
                team_id=team_id,
            ),
            CONTEXT,
        )


async def create_schedule(
    container: Container, actor: User, team_id: UUID | None, name: str = "Scoped schedule"
) -> Schedule:
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(
            actor,
            ScheduleInput(
                name=name,
                template_id="intsum",
                country_iso="UA",
                team_id=team_id,
            ),
            CONTEXT,
        )
