"""Research levels enforce calendar allowances independently of report retention."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ase.application.dto import RequestContext
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.research_usage import ResearchUsageLimit, period_bounds, tier_policy
from ase.domain.users import Role


@pytest.mark.parametrize(
    "tier,limit,period",
    [(1, 4, "week"), (2, 4, "day"), (3, 13, "day"), (4, 32, "day"), (5, None, "day")],
)
def test_tier_allowances(tier, limit, period):
    policy = tier_policy(tier)
    assert (policy.limit, policy.period) == (limit, period)


@pytest.mark.parametrize("tier", [True, False, 0, 6, "1", 1.0])
def test_invalid_tiers(tier):
    with pytest.raises(InvalidRequest):
        tier_policy(tier)


def test_week_starts_monday_and_day_is_utc():
    now = datetime.fromisoformat("2026-09-21T00:30:00+01:00")
    assert period_bounds(now, "day") == (
        datetime(2026, 9, 20, tzinfo=UTC),
        datetime(2026, 9, 21, tzinfo=UTC),
    )
    assert period_bounds(now, "week") == (
        datetime(2026, 9, 14, tzinfo=UTC),
        datetime(2026, 9, 21, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        period_bounds(datetime(2026, 9, 1), "day")


async def test_default_level_for_admin_and_user_and_no_read_charge(container, admin, user):
    async with container.session_factory() as session:
        service = container.research_usage(session)
        for actor in (admin, user):
            allowance = await service.me(actor)
            assert (allowance.tier, allowance.revision, allowance.used, allowance.remaining) == (
                1,
                0,
                0,
                4,
            )
        assert len(await service.list_users(admin)) == 2
        assert (await service.me(user)).used == 0


async def test_limit_persists_between_sessions_and_resets_on_monday(container, user, clock):
    for _ in range(4):
        async with container.session_factory() as session:
            await container.research_usage(session).admit(user, None)
    async with container.session_factory() as session:
        service = container.research_usage(session)
        with pytest.raises(ResearchUsageLimit) as error:
            await service.admit(user, None)
        assert error.value.code == "research_usage_limit"
        assert "4 research runs per week" in error.value.message
        assert error.value.retry_after > 0
        assert (await service.me(user)).used == 4
    clock.advance(timedelta(days=1))
    async with container.session_factory() as session:
        with pytest.raises(ResearchUsageLimit):
            await container.research_usage(session).admit(user, None)
    clock.advance(datetime(2026, 9, 7, tzinfo=UTC) - clock.now())
    async with container.session_factory() as session:
        await container.research_usage(session).admit(user, None)
        assert (await container.research_usage(session).me(user)).used == 1


async def test_tier_changes_preserve_both_counters(container, admin, user, clock):
    async with container.session_factory() as session:
        service = container.research_usage(session)
        for _ in range(4):
            await service.admit(user, None)
        second = await service.assign(admin, user.id, 2, 0, RequestContext())
        assert (second.used, second.remaining) == (4, 0)
        with pytest.raises(ResearchUsageLimit):
            await service.admit(user, None)
        third = await service.assign(admin, user.id, 3, 1, RequestContext())
        assert (third.used, third.remaining) == (4, 9)
        await service.admit(user, None)
        clock.advance(timedelta(days=1))
        assert (await service.me(user)).used == 0
        first = await service.assign(admin, user.id, 1, 2, RequestContext())
        assert (first.used, first.remaining) == (5, 0)
        with pytest.raises(ResearchUsageLimit):
            await service.admit(user, None)


async def test_assignment_checks_revision_and_audits_without_changing_role(container, admin):
    async with container.session_factory() as session:
        service = container.research_usage(session)
        changed = await service.assign(admin, admin.id, 4, 0, RequestContext())
        assert (changed.tier, changed.revision) == (4, 1)
        with pytest.raises(Conflict):
            await service.assign(admin, admin.id, 2, 0, RequestContext())
        repos = container.repositories(session)
        saved = await repos.users.get_by_id(admin.id)
        assert saved.role is Role.ADMIN and saved.is_active
        entries = await repos.audit.list_before(None, 20)
        entries = [entry for entry in entries if entry.action.value == "research_tier_assigned"]
        assert len(entries) == 1
        assert entries[0].details["tier"] == 4


async def test_assignment_revalidates_actor_and_target(container, admin, user):
    async with container.session_factory() as session:
        service = container.research_usage(session)
        with pytest.raises(Forbidden):
            await service.assign(user, user.id, 4, 0, RequestContext())
        with pytest.raises(NotFound):
            await service.assign(admin, uuid4(), 4, 0, RequestContext())
        repos = container.repositories(session)
        fresh = await repos.users.get_by_id(admin.id)
        fresh.role = Role.USER
        await repos.users.save(fresh)
        await session.commit()
        with pytest.raises(Forbidden):
            await service.assign(admin, user.id, 4, 0, RequestContext())
        fresh.is_active = False
        await repos.users.save(fresh)
        await session.commit()
        with pytest.raises(Unauthenticated):
            await service.admit(admin, None)


async def test_locked_admission_rolls_back_with_caller_transaction(container, user):
    async with container.session_factory() as session:
        await container.access_policy(session).context(user, for_update=True)
        await container.research_usage(session).admit_locked(user.id, container.clock.now())
        await session.rollback()
    async with container.session_factory() as session:
        assert (await container.research_usage(session).me(user)).used == 0
