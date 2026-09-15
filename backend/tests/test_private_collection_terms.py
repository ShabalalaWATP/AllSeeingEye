"""Collection vocabulary follows current scope; raw public posts remain shared."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.persistence.social import SqlSocialTerms
from ase.adapters.persistence.watchlists import MAX_PLANS, SqlWatchlistPlanStore
from ase.application.trackers.social import SocialService
from ase.container import Container
from ase.domain.social import vocabulary
from ase.domain.teams import MembershipRole
from ase.domain.users import User
from helpers import create_user
from social_helpers import MemoryActivity, social_plan
from team_helpers import CONTEXT


async def test_current_team_members_see_terms_but_removed_creator_does_not(
    container: Container, admin: User, user: User
) -> None:
    member = await create_user(container, email="member@example.com", password=None)
    outsider = await create_user(container, email="outsider@example.com", password=None)
    async with container.session_factory() as session:
        teams = container.teams(session)
        team = await teams.create(admin, "Team", CONTEXT)
        for actor in (user, member):
            await teams.set_member(
                admin, team.id, email=actor.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
        plans = container.repositories(session).plans
        await plans.add(social_plan(user.id, ["personal secret"]))
        await plans.add(social_plan(member.id, ["member private"]))
        await plans.add(replace(social_plan(user.id, ["team secret"]), team_id=team.id))
        await plans.add(replace(social_plan(member.id, ["team secret"]), team_id=team.id))
        await session.commit()
    source = SqlSocialTerms(container.session_factory, ["public"], container.access_policy)
    board = SocialService(container.store, source, MemoryActivity(), container.clock)
    assert {row.term for row in (await board.board(user)).keywords} == {
        "public",
        "personal secret",
        "team secret",
    }
    assert {row.term for row in (await board.board(member)).keywords} == {
        "public",
        "member private",
        "team secret",
    }
    assert {row.term for row in (await board.board(outsider)).keywords} == {"public"}
    assert len((await board.board(admin)).keywords) == 4
    async with container.session_factory() as session:
        await container.teams(session).remove_member(admin, team.id, user.id, CONTEXT)
    assert {row.term for row in (await board.board(user)).keywords} == {"public", "personal secret"}
    assert "team secret" in {row.term for row in (await board.board(member)).keywords}
    async with container.session_factory() as session:
        await container.teams(session).update(
            admin, team.id, name=None, is_active=False, context=CONTEXT
        )
    assert "team secret" not in {term.term for term in await source.configured()}


async def test_background_queries_drop_deactivated_revoked_and_archived_owners(
    container: Container, admin: User, user: User
) -> None:
    inactive = await create_user(
        container, email="inactive@example.com", password=None, is_active=False
    )
    owner = await create_user(container, email="owner@example.com", password=None)
    async with container.session_factory() as session:
        team = await container.teams(session).create(owner, "Team", CONTEXT)
        await container.teams(session).set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
        plans = container.repositories(session).plans
        personal = social_plan(user.id, ["personal"])
        shared = replace(social_plan(user.id, ["shared"]), team_id=team.id)
        await plans.add(personal)
        await plans.add(shared)
        await plans.add(social_plan(inactive.id, ["inactive"]))
        # Administrator capability cannot keep unattended collection running without membership.
        await plans.add(replace(social_plan(admin.id, ["admin outsider"]), team_id=team.id))
        await session.commit()
    watchlists = SqlWatchlistPlanStore(container.session_factory)
    assert {plan.id for plan in await watchlists.enabled_plans()} == {personal.id, shared.id}
    async with container.session_factory() as session:
        await container.teams(session).remove_member(admin, team.id, user.id, CONTEXT)
    assert {plan.id for plan in await watchlists.enabled_plans()} == {personal.id}
    async with container.session_factory() as session:
        await container.update_user(session).execute(admin, user.id, None, False, CONTEXT)
    assert await watchlists.enabled_plans() == []
    assert (
        await SqlSocialTerms(container.session_factory, [], container.access_policy).configured()
        == ()
    )


async def test_background_eligibility_filters_before_watchlist_limit(
    container: Container, user: User
) -> None:
    inactive = await create_user(
        container, email="inactive@example.com", password=None, is_active=False
    )
    async with container.session_factory() as session:
        plans = container.repositories(session).plans
        for index in range(MAX_PLANS + 1):
            await plans.add(social_plan(inactive.id, [f"ineligible {index}"]))
        eligible = social_plan(user.id, ["eligible"])
        eligible = replace(eligible, created_at=eligible.created_at + timedelta(days=1))
        await plans.add(eligible)
        await session.commit()
    assert [
        plan.id for plan in await SqlWatchlistPlanStore(container.session_factory).enabled_plans()
    ] == [eligible.id]
    terms = await SqlSocialTerms(
        container.session_factory, [], container.access_policy
    ).configured()
    assert [term.term for term in terms] == ["eligible"]


async def test_team_vocabulary_never_grants_creator_personal_visibility(
    container: Container, admin: User, user: User
) -> None:
    async with container.session_factory() as session:
        team = await container.teams(session).create(admin, "Team", CONTEXT)
    terms = vocabulary([], [replace(social_plan(user.id, ["secret"]), team_id=team.id)])
    assert terms[0].owners == frozenset()
    assert terms[0].team_ids == frozenset({team.id})
