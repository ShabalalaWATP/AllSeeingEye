"""Legacy delivery is preserved without reconstructing a hidden sender directory."""

from datetime import timedelta
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from httpx import AsyncClient

from ase.adapters.persistence.team_invitation_models import TeamInvitationReceiptRow
from ase.container import Container
from ase.domain.team_invitation import InvitationStatus, TeamInvitation
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from ase.infrastructure.migrations import alembic_config
from helpers import USER_PASSWORD, bearer, create_user, login_token
from team_helpers import CONTEXT, team_service


async def _upgrade(container: Container) -> None:
    revision = ScriptDirectory.from_config(alembic_config("sqlite+aiosqlite://")).get_revision(
        "0067"
    )
    assert revision is not None

    def upgrade(connection):
        TeamInvitationReceiptRow.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            revision.module.upgrade()

    async with container.engine.begin() as connection:
        await connection.run_sync(upgrade)


async def test_migration_keeps_inbox_but_only_backfills_consented_sender_history(
    container: Container, user: User
) -> None:
    recipient = await create_user(container, email="legacy-private@example.com", password=None)
    async with team_service(container) as service:
        team = await service.create(user, "Legacy desk", CONTEXT)
    now = container.clock.now()
    async with container.session_factory() as session:
        invitations = container.repositories(session).team_invitations
        for status in (
            InvitationStatus.PENDING,
            InvitationStatus.ACCEPTED,
            InvitationStatus.DECLINED,
        ):
            await invitations.add(
                TeamInvitation(
                    id=uuid4(),
                    team_id=team.id,
                    recipient_id=recipient.id,
                    inviter_id=user.id,
                    role=MembershipRole.MEMBER,
                    note=None,
                    status=status,
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                )
            )
        await session.commit()
    await _upgrade(container)
    async with container.session_factory() as session:
        repository = container.repositories(session).team_invitations
        sent = await repository.list_for_team(team.id, status=None, limit=20, offset=0, now=now)
        inbox = await repository.list_for_recipient(
            recipient.id, status=None, limit=20, offset=0, now=now
        )
        assert sent.total == 1 and sent.items[0].status is InvitationStatus.ACCEPTED
        assert sent.items[0].recipient_id == recipient.id
        assert sent.items[0].recipient_username is None
        assert sent.items[0].recipient_display_name is None
        assert inbox.total == 3


async def test_migrated_pending_delivery_remains_revocable_without_sender_disclosure(
    client: AsyncClient, container: Container, user: User
) -> None:
    recipient = await create_user(
        container, email="legacy-revoke@example.com", password=USER_PASSWORD
    )
    async with team_service(container) as service:
        team = await service.create(user, "Legacy revoke", CONTEXT)
        other_team = await service.create(user, "Other desk", CONTEXT)
    now, delivery_id = container.clock.now(), uuid4()
    async with container.session_factory() as session:
        await container.repositories(session).team_invitations.add(
            TeamInvitation(
                id=delivery_id,
                team_id=team.id,
                recipient_id=recipient.id,
                inviter_id=user.id,
                role=MembershipRole.MEMBER,
                note=None,
                status=InvitationStatus.PENDING,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        await session.commit()
    await _upgrade(container)
    sender = bearer(await login_token(client, user.email, USER_PASSWORD))
    recipient_headers = bearer(await login_token(client, recipient.email, USER_PASSWORD))
    path = f"/api/teams/{team.id}/invitations"
    assert (await client.get(path, headers=sender)).json()["total"] == 0
    # Missing and wrong-team IDs reveal no state and cannot revoke another team's grant.
    for target in (path + f"/{uuid4()}", f"/api/teams/{other_team.id}/invitations/{delivery_id}"):
        response = await client.delete(target, headers=sender, params={"expected_revision": 99})
        assert response.status_code == 204 and not response.content
    inbox = (await client.get("/api/me/team-invitations", headers=recipient_headers)).json()
    assert inbox["items"][0]["id"] == str(delivery_id)
    for _ in range(2):
        response = await client.delete(
            path + f"/{delivery_id}", headers=sender, params={"expected_revision": 99}
        )
        assert response.status_code == 204 and not response.content
    assert (await client.get(path, headers=sender)).json()["total"] == 0
    accepted = await client.post(
        f"/api/me/team-invitations/{delivery_id}/accept", headers=recipient_headers, json={}
    )
    assert accepted.status_code == 409
