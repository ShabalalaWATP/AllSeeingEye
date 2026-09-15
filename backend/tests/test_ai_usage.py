"""Durable AI allowance admission and settlement behaviour."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.ai_usage import SqlAiUsageRepository
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.application.ai_usage import AiPolicyInput, AiUsageAccounting, AiUsagePolicyAdmin
from ase.domain.ai_usage import (
    AiAllowanceExceeded,
    AiAllowancePeriod,
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

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def policy(*, limit: int | None = 2, tokens: int | None = 100) -> AiUsagePolicy:
    return AiUsagePolicy(
        uuid4(),
        AiPolicyScope.GLOBAL,
        None,
        AiAllowancePeriod.MONTH,
        limit,
        tokens,
        True,
        1,
        NOW,
        NOW,
    )


def actor(role: Role = Role.ADMIN) -> User:
    return User(
        uuid4(),
        "admin@example.com",
        "Admin",
        role,
        True,
        "hash",
        0,
        None,
        None,
        NOW,
        None,
    )


async def add_policy(container, current: AiUsagePolicy) -> None:
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        await repo.add_policy(current)
        await session.commit()


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
    current = policy(limit=2, tokens=100)
    await add_policy(container, current)
    accounting = AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
    )
    batch = await accounting.reserve(
        user.id,
        profile_id=None,
        model="fixture-model",
        purpose="test",
        requested_tokens=80,
    )
    assert batch is not None and len(batch.reservations) == 1
    assert batch.reservations[0].status is AiReservationStatus.RESERVED
    await accounting.settle(
        batch,
        ok=True,
        prompt_tokens=20,
        completion_tokens=30,
        error=None,
    )
    await accounting.settle(
        batch,
        ok=True,
        prompt_tokens=20,
        completion_tokens=30,
        error=None,
    )
    async with container.session_factory() as session:
        summaries = await container.repositories(session).ai_usage.summary(user.id, now=NOW)
        reservations = await container.repositories(session).ai_usage.list_reservations()
    assert summaries[0].used_requests == 1
    assert summaries[0].reserved_requests == 0
    assert summaries[0].used_tokens == 50
    assert reservations[0].actual_tokens == 50


async def test_zero_is_deny_all_and_none_is_unlimited(container, user):
    deny = policy(limit=0, tokens=0)
    await add_policy(container, deny)
    accounting = AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
    )
    with pytest.raises(AiAllowanceExceeded):
        await accounting.reserve(
            user.id,
            profile_id=None,
            model="fixture-model",
            purpose="test",
            requested_tokens=1,
        )
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
        unlimited = policy(limit=None, tokens=None)
        await repo.add_policy(unlimited)
        await session.commit()
    unlimited_batch = await accounting.reserve(
        user.id,
        profile_id=None,
        model="fixture-model",
        purpose="test",
        requested_tokens=1,
    )
    assert unlimited_batch is not None


async def test_new_calendar_period_has_fresh_allowance(container, user, clock):
    current = policy(limit=1, tokens=100)
    await add_policy(container, current)
    accounting = AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
    )
    first = await accounting.reserve(
        user.id,
        profile_id=None,
        model="fixture-model",
        purpose="test",
        requested_tokens=10,
    )
    assert first is not None
    await accounting.settle(first, ok=True, prompt_tokens=2, completion_tokens=3, error=None)
    with pytest.raises(AiAllowanceExceeded):
        await accounting.reserve(
            user.id,
            profile_id=None,
            model="fixture-model",
            purpose="test",
            requested_tokens=10,
        )
    clock.advance(timedelta(days=31))
    second = await accounting.reserve(
        user.id,
        profile_id=None,
        model="fixture-model",
        purpose="test",
        requested_tokens=10,
    )
    assert second is not None


async def test_policy_admin_requires_admin_and_rejects_duplicate(container, user):
    # Use a real request session so the application service sees the same repository
    # contract as the HTTP routes.
    async with container.session_factory() as session:
        admin_service = AiUsagePolicyAdmin(
            container.repositories(session).ai_usage, container.clock
        )
        with pytest.raises(Forbidden):
            await admin_service.list(user)
        current = await admin_service.create(
            actor(), AiPolicyInput(AiPolicyScope.GLOBAL, None, AiAllowancePeriod.DAY, 5, 100, True)
        )
        with pytest.raises(Conflict):
            await admin_service.create(
                actor(),
                AiPolicyInput(AiPolicyScope.GLOBAL, None, AiAllowancePeriod.DAY, 5, 100, True),
            )
        updated = await admin_service.update(
            actor(),
            current.id,
            AiPolicyInput(AiPolicyScope.GLOBAL, None, AiAllowancePeriod.DAY, 0, 100, True),
        )
        assert updated.revision == 2
        await session.commit()


async def test_file_backed_concurrent_reservations_refuse_the_loser(tmp_path):
    database = tmp_path / "ai-usage.db"
    engine = create_engine(f"sqlite+aiosqlite:///{database}")
    factory = create_session_factory(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    current = policy(limit=1, tokens=10)
    async with factory() as session:
        repo = SqlAiUsageRepository(session)
        await repo.add_policy(current)
        await session.commit()

    async def attempt() -> bool:
        async with factory() as session:
            repo = SqlAiUsageRepository(session)
            try:
                await repo.reserve(
                    current.id,
                    user_id=uuid4(),
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
    current = policy(limit=1, tokens=32_000)
    await add_policy(container, current)
    async with container.session_factory() as session:
        answer = await container.map_assistant(session).execute(
            user,
            AssistantQuestion("Recent earthquakes"),
            check_session=nothing,
        )
    assert answer.model is not None
    async with container.session_factory() as session:
        with pytest.raises(AiAllowanceExceeded):
            await container.map_assistant(session).execute(
                user,
                AssistantQuestion("Recent earthquakes"),
                check_session=nothing,
            )
        reservations = await container.repositories(session).ai_usage.list_reservations()
    assert len(reservations) == 1
    assert reservations[0].profile_id == selected.id
    assert reservations[0].status is AiReservationStatus.SETTLED


async def test_team_policy_requires_an_explicit_team_destination(container, user):
    team_id = uuid4()
    team_policy = AiUsagePolicy(
        uuid4(),
        AiPolicyScope.TEAM,
        team_id,
        AiAllowancePeriod.MONTH,
        1,
        10,
        True,
        1,
        NOW,
        NOW,
    )
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
        repo = container.repositories(session).ai_usage
        await repo.add_policy(team_policy)
        await session.commit()
    accounting = AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
    )
    assert (
        await accounting.reserve(
            user.id,
            profile_id=None,
            model="fixture-model",
            purpose="personal",
            requested_tokens=1,
        )
        is None
    )
    team_batch = await accounting.reserve(
        user.id,
        team_id=team_id,
        profile_id=None,
        model="fixture-model",
        purpose="team",
        requested_tokens=1,
    )
    assert team_batch is not None
