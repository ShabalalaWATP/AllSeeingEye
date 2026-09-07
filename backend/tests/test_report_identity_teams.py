"""Team identity review follows current membership, authorship and archive policy."""

import pytest
from sqlalchemy import update

from ase.adapters.persistence.models import ReportRow
from ase.application.reports import identities
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from team_helpers import CONTEXT, team_service
from test_report_identity_service import VALUE, create, seed_report
from test_report_team_scope import team_for
from test_saved_map_views import claims_for


async def team_report(container, author, team):
    record, version = await seed_report(container, author)
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == record.id).values(team_id=team.id)
        )
        await session.commit()
    return record, version


async def test_member_creates_on_shared_report_then_revocation_hides_history(
    client, container, admin, user
):
    team = await team_for(container, admin, user)
    claims = await claims_for(client, container, user)
    record, _ = await team_report(container, admin, team)
    first = await create(container, claims, record)
    async with container.session_factory() as session:
        root, _ = await container.report_identities(session).get(claims, first.decision_id)
        assert root.created_by == user.id and root.team_id == team.id
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    async with container.session_factory() as session:
        service = container.report_identities(session)
        with pytest.raises(NotFound):
            await service.get(claims, first.decision_id, first.id)
        with pytest.raises(NotFound):
            await service.list(claims, record.id, 1)
        with pytest.raises(NotFound):
            await service.update(claims, first.decision_id, first.id, VALUE, CONTEXT)


async def test_other_member_reads_but_cannot_correct_existing_review(
    client, container, admin, user
):
    team = await team_for(container, admin, user)
    user_claims = await claims_for(client, container, user)
    admin_claims = await claims_for(client, container, admin)
    record, _ = await team_report(container, user, team)
    first = await create(container, admin_claims, record)
    async with container.session_factory() as session:
        service = container.report_identities(session)
        assert (await service.get(user_claims, first.decision_id))[1] == first
        with pytest.raises(Forbidden):
            await service.update(user_claims, first.decision_id, first.id, VALUE, CONTEXT)
        with pytest.raises(Conflict, match="already"):
            await service.create(user_claims, record.id, 1, VALUE, CONTEXT)


async def test_archive_allows_read_and_admin_override_only(client, container, admin, user):
    team = await team_for(container, admin, user)
    user_claims = await claims_for(client, container, user)
    record, _ = await team_report(container, user, team)
    first = await create(container, user_claims, record)
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    admin_claims = await claims_for(client, container, admin)
    async with container.session_factory() as session:
        service = container.report_identities(session)
        assert (await service.get(user_claims, first.decision_id))[1] == first
        with pytest.raises(Forbidden):
            await service.update(user_claims, first.decision_id, first.id, VALUE, CONTEXT)
        with pytest.raises(Forbidden):
            await service.create(user_claims, record.id, 1, VALUE, CONTEXT)
        second = await service.update(admin_claims, first.decision_id, first.id, VALUE, CONTEXT)
        assert second.authored_by == admin.id and second.number == 2


async def test_team_quota_is_shared_across_authors(client, container, admin, user, monkeypatch):
    team = await team_for(container, admin, user)
    user_claims = await claims_for(client, container, user)
    admin_claims = await claims_for(client, container, admin)
    first_report, _ = await team_report(container, user, team)
    second_report, _ = await team_report(container, admin, team)
    await create(container, user_claims, first_report)
    monkeypatch.setattr(identities, "MAX_SCOPE_DECISIONS", 1)
    with pytest.raises(InvalidRequest, match="limit"):
        await create(container, admin_claims, second_report)
