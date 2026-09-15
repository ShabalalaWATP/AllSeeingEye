"""Invitation expiry, outstanding caps, roster caps and non-enumerating refusals."""

from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.teams import invitations as invitation_module
from ase.application.teams import service as service_module
from ase.container import Container
from ase.domain.directory_profile import DirectoryProfile
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.team_invitation import InvitationStatus
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User
from helpers import FakeClock, create_user
from team_helpers import CONTEXT, team_service


async def _listed(container: Container, email: str, handle: str, **kwargs: object) -> User:
    account = await create_user(container, email=email, password=None, **kwargs)  # type: ignore[arg-type]
    async with container.session_factory() as session:
        await container.repositories(session).directory_profiles.save(
            DirectoryProfile(account.id, username=handle, is_discoverable=True)
        )
        await session.commit()
    return account


async def test_lapsed_invitation_expires_and_allows_reinvitation(
    container: Container, user: User, clock: FakeClock
) -> None:
    recipient = await _listed(container, "recipient@example.com", "recipient")
    async with team_service(container) as service:
        team = await service.create(user, "Desk", CONTEXT)
    async with container.session_factory() as session:
        first = await container.team_invitations(session).send(
            user, team.id, recipient.id, None, CONTEXT
        )
    clock.advance(timedelta(days=8))
    async with container.session_factory() as session:
        invitations = container.team_invitations(session)
        pending = await invitations.inbox(
            recipient, status=InvitationStatus.PENDING, limit=20, offset=0
        )
        assert pending.total == 0 and pending.items == ()
        expired = await invitations.inbox(
            recipient, status=InvitationStatus.EXPIRED, limit=20, offset=0
        )
        assert [item.id for item in expired.items] == [first.id]
        assert expired.items[0].status is InvitationStatus.EXPIRED
        everything = await invitations.team_inbox(user, team.id, status=None, limit=20, offset=0)
        assert everything.items[0].status is InvitationStatus.EXPIRED
    async with container.session_factory() as session:
        second = await container.team_invitations(session).send(
            user, team.id, recipient.id, None, CONTEXT
        )
    assert second.id != first.id and second.status is InvitationStatus.PENDING
    async with container.session_factory() as session:
        stored = await container.repositories(session).team_invitations.get(first.id)
    assert stored is not None and stored.status is InvitationStatus.EXPIRED
    assert stored.responded_at is None


async def test_lapsed_invitations_do_not_consume_the_outstanding_cap(
    container: Container, user: User, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(invitation_module, "MAX_PENDING_INVITATIONS", 2)
    recipients = [
        await _listed(container, f"r{index}@example.com", f"recipient_{index}")
        for index in range(4)
    ]
    async with team_service(container) as service:
        team = await service.create(user, "Desk", CONTEXT)
    for recipient in recipients[:2]:
        async with container.session_factory() as session:
            await container.team_invitations(session).send(
                user, team.id, recipient.id, None, CONTEXT
            )
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="pending invitation limit"):
            await container.team_invitations(session).send(
                user, team.id, recipients[2].id, None, CONTEXT
            )
    clock.advance(timedelta(days=8))
    for recipient in recipients[2:]:
        async with container.session_factory() as session:
            await container.team_invitations(session).send(
                user, team.id, recipient.id, None, CONTEXT
            )
    async with container.session_factory() as session:
        repository = container.repositories(session).team_invitations
        assert await repository.count_pending(team.id, clock.now()) == 2


async def test_accepting_an_invitation_respects_the_roster_cap(
    container: Container, user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(invitation_module, "MAX_TEAM_MEMBERS", 2)
    first = await _listed(container, "first@example.com", "first_recipient")
    second = await _listed(container, "second@example.com", "second_recipient")
    async with team_service(container) as service:
        team = await service.create(user, "Desk", CONTEXT)
    sent = []
    for recipient in (first, second):
        async with container.session_factory() as session:
            sent.append(
                await container.team_invitations(session).send(
                    user, team.id, recipient.id, None, CONTEXT
                )
            )
    async with container.session_factory() as session:
        await container.team_invitations(session).accept(first, sent[0].id, CONTEXT, None)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="at most 2 members"):
            await container.team_invitations(session).accept(second, sent[1].id, CONTEXT, None)
    async with team_service(container) as service:
        members = {member.user_id for member in (await service.roster(user, team.id))[1]}
    assert members == {user.id, first.id}
    assert service_module.MAX_TEAM_MEMBERS == 100


async def test_manager_invitation_refusals_do_not_distinguish_accounts(
    container: Container, admin: User, user: User
) -> None:
    hidden = await create_user(container, email="hidden@example.com", password=None)
    inactive = await _listed(container, "inactive@example.com", "inactive_one", is_active=False)
    listed_admin = await _listed(container, "boss@example.com", "site_boss", role=Role.ADMIN)
    async with team_service(container) as service:
        team = await service.create(user, "Desk", CONTEXT)
    messages = set()
    for recipient_id in (hidden.id, inactive.id, listed_admin.id, uuid4()):
        async with container.session_factory() as session:
            with pytest.raises(InvalidRequest) as caught:
                await container.team_invitations(session).send(
                    user, team.id, recipient_id, None, CONTEXT
                )
            messages.add(str(caught.value))
    assert len(messages) == 1
    # An Administrator may still invite another listed Administrator.
    async with team_service(container) as service:
        admin_team = await service.create(admin, "Admin desk", CONTEXT)
    async with container.session_factory() as session:
        invitation = await container.team_invitations(session).send(
            admin, admin_team.id, listed_admin.id, None, CONTEXT
        )
    assert invitation.role is MembershipRole.MEMBER
    async with container.session_factory() as session:
        with pytest.raises(Conflict):
            await container.team_invitations(session).send(
                admin, admin_team.id, listed_admin.id, None, CONTEXT
            )
