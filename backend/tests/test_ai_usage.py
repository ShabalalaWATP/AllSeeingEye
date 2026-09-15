"""Durable AI allowance admission and settlement behaviour."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ai_usage_helpers import NOW, accounting, add_policy, policy, reservations, summaries
from ase.adapters.persistence.ai_usage import SqlAiUsageRepository
from ase.adapters.persistence.session import create_session_factory
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.application.ai_usage_admin import AiPolicyInput, AiUsagePolicyAdmin
from ase.domain.ai_usage import (
    AiAllowanceExceeded,
    AiAllowancePeriod,
    AiAttribution,
    AiCallOutcome,
    AiPolicyScope,
    AiReservationStatus,
    AiUsagePolicy,
    period_bounds,
)
from ase.domain.assistant import AssistantQuestion
from ase.domain.errors import Conflict, Forbidden
from ase.domain.users import Role, User
from assistant_helpers import Admission, Gateway, event, nothing
from assistant_helpers import profile as eye_profile
from race_database import race_engine


def actor(role: Role = Role.ADMIN) -> User:
    return User(uuid4(), "admin@example.com", "Admin", role, True, "hash", 0, None, None, NOW, None)


async def reserve(container, user_id, *, team_id=None, tokens=10):
    return await accounting(container).reserve(
        AiAttribution.actor(user_id, team_id),
        profile_id=None,
        model="fixture-model",
        purpose="test",
        requested_tokens=tokens,
    )


async def test_period_bounds_use_calendar_windows_and_reset() -> None:
    start, end = period_bounds(datetime(2026, 9, 16, 12, tzinfo=UTC), AiAllowancePeriod.WEEK)
    assert start == datetime(2026, 9, 14, tzinfo=UTC)
    assert end == datetime(2026, 9, 21, tzinfo=UTC)
    month_start, month_end = period_bounds(
        datetime(2026, 12, 31, 23, tzinfo=UTC), AiAllowancePeriod.MONTH
    )
    assert month_start == datetime(2026, 12, 1, tzinfo=UTC)
    assert month_end == datetime(2027, 1, 1, tzinfo=UTC)


async def test_reservation_settlement_is_idempotent_and_counts_actual_tokens(container, user):
    await add_policy(container, policy(limit=2, tokens=100))
    ledger = accounting(container)
    batch = await reserve(container, user.id, tokens=80)
    assert len(batch.reservations) == 1
    assert batch.reservations[0].status is AiReservationStatus.RESERVED
    for _ in range(2):
        await ledger.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=20, completion_tokens=30)
    current = await summaries(container, user.id)
    rows = await reservations(container)
    assert current[0].used_requests == 1
    assert current[0].reserved_requests == 0
    assert current[0].used_tokens == 50
    assert rows[0].actual_tokens == 50
    async with container.session_factory() as session:
        totals = await container.repositories(session).ai_usage.account_totals(
            user.id, container.clock.now()
        )
    assert (totals.used_requests, totals.used_tokens) == (1, 50)


async def test_zero_is_deny_all_and_none_is_unlimited(container, user):
    deny = policy(limit=0, tokens=0)
    await add_policy(container, deny)
    with pytest.raises(AiAllowanceExceeded):
        await reserve(container, user.id, tokens=1)
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        disabled = await repo.get_policy(deny.id)
        assert disabled is not None
        await repo.save_policy(
            AiUsagePolicy(
                disabled.id,
                disabled.scope,
                disabled.target_id,
                disabled.period,
                disabled.request_limit,
                disabled.token_limit,
                False,
                disabled.revision + 1,
                disabled.created_at,
                NOW,
            )
        )
        await repo.add_policy(policy(limit=None, tokens=None))
        await session.commit()
    assert len((await reserve(container, user.id, tokens=1)).reservations) == 1


async def test_new_calendar_period_has_fresh_allowance(container, user, clock):
    await add_policy(container, policy(limit=1, tokens=100))
    first = await reserve(container, user.id)
    await accounting(container).finish(
        first, AiCallOutcome.COMPLETED, prompt_tokens=2, completion_tokens=3
    )
    with pytest.raises(AiAllowanceExceeded):
        await reserve(container, user.id)
    clock.advance(timedelta(days=31))
    assert (await reserve(container, user.id)).reservations


async def test_policy_admin_requires_admin_and_rejects_duplicate(container, user):
    async with container.session_factory() as session:
        admin_service = AiUsagePolicyAdmin(
            container.repositories(session).ai_usage, container.clock
        )
        with pytest.raises(Forbidden):
            await admin_service.list(user)
        data = AiPolicyInput(AiPolicyScope.GLOBAL, None, AiAllowancePeriod.DAY, 5, 100, True)
        current = await admin_service.create(actor(), data)
        with pytest.raises(Conflict):
            await admin_service.create(actor(), data)
        system = await admin_service.create(
            actor(), AiPolicyInput(AiPolicyScope.SYSTEM, None, AiAllowancePeriod.DAY, 5, 9, True)
        )
        assert system.scope is AiPolicyScope.SYSTEM
        updated = await admin_service.update(
            actor(),
            current.id,
            AiPolicyInput(AiPolicyScope.GLOBAL, None, AiAllowancePeriod.DAY, 0, 100, True),
        )
        assert updated.revision == 2
        await session.commit()


async def test_file_backed_concurrent_reservations_refuse_the_loser(tmp_path):
    engine = await race_engine(tmp_path, "ai-usage.db")
    factory = create_session_factory(engine)
    current = policy(limit=1, tokens=10)
    async with factory() as session:
        await SqlAiUsageRepository(session).add_policy(current)
        await session.commit()

    async def attempt() -> bool:
        async with factory() as session:
            repo = SqlAiUsageRepository(session)
            try:
                await repo.reserve(
                    current.id,
                    call_id=uuid4(),
                    attribution=AiAttribution.system_work(),
                    profile_id=None,
                    model="fixture-model",
                    purpose="race",
                    requested_tokens=10,
                    now=NOW,
                )
                await session.commit()
                return True
            except AiAllowanceExceeded:
                await session.rollback()
                return False

    outcomes = await asyncio.gather(attempt(), attempt())
    assert sorted(outcomes) == [False, True]
    await engine.dispose()


async def test_ask_eye_reserves_and_settles_before_allowing_next_request(container, user):
    selected = await eye_profile(container)
    container.llm = Gateway()
    container.source_admission = Admission()
    container.store.upsert((event(),))
    await add_policy(container, policy(limit=1, tokens=64_000))
    async with container.session_factory() as session:
        answer = await container.map_assistant(session).execute(
            user, AssistantQuestion("Recent earthquakes"), check_session=nothing
        )
    assert answer.model is not None
    async with container.session_factory() as session:
        with pytest.raises(AiAllowanceExceeded):
            await container.map_assistant(session).execute(
                user, AssistantQuestion("Recent earthquakes"), check_session=nothing
            )
    rows = await reservations(container)
    assert len(rows) == 1
    assert rows[0].profile_id == selected.id
    assert rows[0].status is AiReservationStatus.SETTLED
    assert rows[0].dispatched_at is not None


async def test_team_policy_requires_an_explicit_team_destination(container, user):
    team_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            TeamRow(
                id=team_id,
                name="Team",
                is_active=True,
                created_by=user.id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            TeamMembershipRow(team_id=team_id, user_id=user.id, role="member", joined_at=NOW)
        )
        await session.commit()
    await add_policy(
        container, policy(limit=1, tokens=10, scope=AiPolicyScope.TEAM, target_id=team_id)
    )
    personal = await reserve(container, user.id, tokens=1)
    assert personal.reservations == ()
    team_batch = await reserve(container, user.id, team_id=team_id, tokens=1)
    assert len(team_batch.reservations) == 1
    assert team_batch.reservations[0].team_id == team_id
    # A non-member cannot charge, and therefore cannot exhaust, another team's allowance.
    outsider = await reserve(container, uuid4(), team_id=team_id, tokens=1)
    assert outsider.reservations == () and outsider.attribution.team_id is None
