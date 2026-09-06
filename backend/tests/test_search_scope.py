"""Scoped embedding work never discards another scope or returns revoked work."""

from datetime import timedelta

import pytest

from ase.application.reports import search as search_module
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from report_documents_helpers import document_records
from report_search_helpers import FakeEmbeddings, add_profile, add_report, service
from team_helpers import CONTEXT, team_service


async def test_older_personal_report_is_indexable_without_deleting_other_scopes(
    container: Container, user: User, admin: User, monkeypatch
) -> None:
    monkeypatch.setattr(search_module, "MAX_REPORTS", 2)
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        own, _ = await add_report(container, session, user)
        for index in range(2):
            record, version = document_records(admin.id)
            record.created_at = own.created_at + timedelta(seconds=index + 1)
            await container.repositories(session).reports.add(record, version)
        await session.commit()
        search = service(container, session, gateway)
        assert (await search.index(user)).indexed == 1
        assert (await search.index(user)).indexed == 1
        assert len(gateway.calls) == 1
        # Only one of the administrator's two new reports fits the remaining slot.
        await search.index(admin)
        assert (await search.status(user)).indexed == 1
        calls = len(gateway.calls)
        with pytest.raises(InvalidRequest, match="storage limit"):
            await search.index(admin)
        assert len(gateway.calls) == calls


@pytest.mark.parametrize("operation", ["index", "query"])
async def test_search_rechecks_membership_after_embedding(
    container: Container, user: User, admin: User, operation: str
) -> None:
    async with team_service(container) as teams:
        team = await teams.create(admin, "Team evidence", CONTEXT)
        await teams.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    gateway = FakeEmbeddings()
    async with container.session_factory() as session:
        await add_profile(container, session)
        record, version = document_records(user.id)
        record.team_id = team.id
        await container.repositories(session).reports.add(record, version)
        await session.commit()
        search = service(container, session, gateway)
        if operation == "query":
            await search.index(user)

        async def revoke() -> None:
            async with team_service(container) as teams:
                await teams.remove_member(admin, team.id, user.id, CONTEXT)

        gateway.during_call = revoke
        if operation == "index":
            with pytest.raises(NotFound):
                await search.index(user)
            await session.rollback()
        else:
            result = await search.query(user, "Private question")
            assert not result.items and result.total == 0
        assert (await search.status(user)).total == 0
