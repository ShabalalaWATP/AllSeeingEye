"""Revoked team membership closes both feed and pending delivery visibility."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import delete, update

from ase.adapters.persistence.operational_models import AlertRow, ScheduleRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_notification_delivery import _enqueue, _rows, setup_delivery
from test_private_feed import ATOM, PATH, _alert, feed_auth


async def _team(container, user):
    team_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            TeamRow(
                id=team_id,
                name="Test team",
                is_active=True,
                created_by=user.id,
                created_at=container.clock.now(),
                updated_at=container.clock.now(),
            )
        )
        await session.flush()
        session.add(
            TeamMembershipRow(
                team_id=team_id,
                user_id=user.id,
                role="member",
                joined_at=container.clock.now(),
            )
        )
        await session.commit()
    return team_id


async def test_feed_team_removal_and_completed_editions(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    team_id = await _team(container, user)
    await _alert(container, user)
    schedule, edition, _store = await setup_delivery(container, user)
    async with container.session_factory() as session:
        await session.execute(update(AlertRow).values(team_id=team_id))
        await session.execute(
            update(ScheduleRow).where(ScheduleRow.id == schedule.id).values(team_id=team_id)
        )
        await session.execute(
            update(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.id == edition.id)
            .values(workflow="completed")
        )
        await session.commit()
    issued = await client.post(PATH, headers=bearer(token), json={"include_titles": True})
    headers = feed_auth(issued.json()["token"])
    result = await client.get(ATOM, headers=headers)
    assert "Private alert" in result.text and "Daily research" in result.text
    assert "SECRET" not in result.text
    async with container.session_factory() as session:
        await session.execute(delete(TeamMembershipRow).where(TeamMembershipRow.team_id == team_id))
        await session.commit()
    result = await client.get(ATOM, headers=headers)
    assert result.status_code == 200
    assert "Private alert" not in result.text and "Daily research" not in result.text


async def test_pending_team_email_cancelled_after_removal(container, user):
    team_id = await _team(container, user)
    schedule, edition, store = await setup_delivery(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(ScheduleRow).where(ScheduleRow.id == schedule.id).values(team_id=team_id)
        )
        await session.commit()
    await _enqueue(container, edition)
    claim = await store.claim(container.clock.now())
    assert claim is not None
    async with container.session_factory() as session:
        await session.execute(delete(TeamMembershipRow).where(TeamMembershipRow.team_id == team_id))
        await session.commit()
    assert await store.prepare(claim, container.clock.now()) is None
    assert (await _rows(container))[0].safe_reason == "access_revoked"
