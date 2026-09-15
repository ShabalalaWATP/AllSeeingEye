"""Monitor deletion requires both global and scoped management capability."""

import pytest
from sqlalchemy import update

from annotation_comparison_helpers import prepared
from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.operational_models import ReportRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.errors import Forbidden
from ase.domain.teams import MembershipRole
from ase.domain.users import Role
from helpers import USER_PASSWORD, create_user
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for
from test_saved_map_views import claims_for


@pytest.mark.parametrize(
    "role,membership,allowed",
    [
        (Role.USER, MembershipRole.MEMBER, False),
        (Role.MANAGER, MembershipRole.MEMBER, False),
        (Role.USER, MembershipRole.MANAGER, True),
        (Role.MANAGER, MembershipRole.MANAGER, True),
        (Role.ADMIN, None, True),
    ],
)
async def test_delete_shares_existing_scope_manager_policy_and_preserves_parent(
    client, container, user, admin, role, membership, allowed
):
    team = await team_for(container, admin, user)
    owner, report, _, _, request = await prepared(client, container, user)
    actor_user = (
        admin
        if role is Role.ADMIN
        else await create_user(
            container, email="monitor-reviewer@example.com", password=USER_PASSWORD, role=role
        )
    )
    if role is Role.USER and membership is MembershipRole.MANAGER:
        # Deliberately seed the membership directly so this case verifies that
        # team leadership is sufficient without a legacy global Manager role.
        async with container.session_factory() as session:
            session.add(
                TeamMembershipRow(
                    team_id=team.id,
                    user_id=actor_user.id,
                    role=membership.value,
                    joined_at=container.clock.now(),
                )
            )
            await session.commit()
    elif membership is not None:
        async with team_service(container) as teams:
            await teams.set_member(
                admin, team.id, email=actor_user.email, role=membership, context=CONTEXT
            )
    actor = await claims_for(client, container, actor_user)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == report.id).values(team_id=team.id)
        )
        await session.execute(
            update(ClaimRow).where(ClaimRow.report_id == report.id).values(team_id=team.id)
        )
        await session.commit()
        service = container.annotation_monitors(session)
        monitor = await service.create(
            owner, "Shared selected roots", request.before, ("claim",), True
        )
        if allowed:
            await service.delete(actor, monitor.id, monitor.revision)
            assert await service.repository.get(monitor.id) is None
        else:
            with pytest.raises(Forbidden):
                await service.delete(actor, monitor.id, monitor.revision)
            assert await service.repository.get(monitor.id) is not None
        assert await container.repositories(session).reports.get(report.id) is not None
