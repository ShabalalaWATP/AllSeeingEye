"""Durable daily admission, rolling freshness, isolation and no implicit paid retry."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.persistence.users import SqlUserRepository
from ase.application.daily_briefing import DailyBriefingService, briefing_key, briefing_request
from ase.application.dto import RequestContext
from ase.domain.daily_briefing import retains_daily_admission
from ase.domain.errors import Forbidden, InvalidRequest, Unauthenticated
from ase.domain.events import Category
from ase.domain.research import ResearchMode
from report_job_helpers import NOW, job
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401


def daily(service, deps, guard=None):
    return DailyBriefingService(service, deps.repo, deps.uow, deps.clock, guard or asyncio.Lock())


async def ensure(service, actor):
    return await service.ensure(actor, RequestContext(), check_session=AsyncMock())


def test_request_is_basic_bounded_global_and_coverage_conscious():
    request = briefing_request()
    assert request.research_mode == ResearchMode.QUICK
    assert request.window_hours == 24 and request.report_style == "briefing"
    assert request.team_id is None and not request.research_web_search
    assert {Category.CONFLICT, Category.DISASTER} <= set(request.categories)
    assert "missing or stale" in request.question


async def test_repeated_admission_across_service_restart_reuses_job(service_env):
    env = service_env
    async with env.service() as (service, deps):
        first = await ensure(daily(service, deps), env.user)
        assert first.next_refresh_at == NOW + timedelta(hours=24)
        assert first.job["status"] == "queued"
        assert deps.prepare_job.await_count == 1
    async with env.service() as (service, deps):
        second = await ensure(daily(service, deps), env.user)
        assert second.job["id"] == first.job["id"]
        deps.prepare_job.assert_not_awaited()


async def test_utc_midnight_does_not_refresh_before_24_hours(service_env):
    env = service_env
    async with env.service() as (service, deps):
        first = await ensure(daily(service, deps), env.user)
    before = SimpleNamespace(now=lambda: NOW + timedelta(hours=23, minutes=59))
    async with env.service(clock=before) as (service, deps):
        second = await ensure(daily(service, deps), env.user)
        assert second.job["id"] == first.job["id"]
        deps.prepare_job.assert_not_awaited()
    after = SimpleNamespace(now=lambda: NOW + timedelta(hours=24))
    async with env.service(clock=after) as (service, deps):
        third = await ensure(daily(service, deps), env.user)
        assert third.job["id"] != first.job["id"]
        assert third.next_refresh_at == NOW + timedelta(hours=48)


async def test_midnight_preparation_reuses_two_calendar_dates_old_key(service_env):
    env = service_env
    instant = [NOW.replace(hour=23, minute=59)]
    clock = SimpleNamespace(now=lambda: instant[0])
    async with env.service(clock=clock) as (service, deps):
        prepare = deps.prepare_job.side_effect

        async def across_midnight(*args):
            result = await prepare(*args)
            instant[0] = (NOW + timedelta(days=1)).replace(hour=0, minute=1)
            return result

        deps.prepare_job.side_effect = across_midnight
        first = await ensure(daily(service, deps), env.user)
        deps.prepare_job.side_effect = prepare
        instant[0] = (NOW + timedelta(days=2)).replace(hour=0, minute=0)
        still_fresh = await ensure(daily(service, deps), env.user)
        assert still_fresh.job["id"] == first.job["id"]
        assert deps.prepare_job.await_count == 1
        instant[0] += timedelta(minutes=1)
        refreshed = await ensure(daily(service, deps), env.user)
        assert refreshed.job["id"] != first.job["id"]
        assert deps.prepare_job.await_count == 2


async def test_simultaneous_tabs_only_admit_once(service_env):
    env, guard = service_env, asyncio.Lock()

    async def open_tab():
        async with env.service() as (service, deps):
            return await ensure(daily(service, deps, guard), env.user)

    results = await asyncio.gather(open_tab(), open_tab(), open_tab())
    assert len({row.job["id"] for row in results}) == 1


async def test_personal_briefing_never_reuses_another_owners_job(service_env):
    env = service_env
    async with env.service() as (service, deps):
        own = await ensure(daily(service, deps), env.user)
        other = await ensure(daily(service, deps), env.stranger)
        assert own.job["id"] != other.job["id"]
        assert briefing_key(env.user.id, NOW) != briefing_key(env.stranger.id, NOW)


async def test_paused_job_is_returned_without_automatic_resume(service_env):
    env = service_env
    async with env.service() as (service, deps):
        first = await ensure(daily(service, deps), env.user)
        await service.pause(env.user, first.job["id"], check_session=AsyncMock())
        again = await ensure(daily(service, deps), env.user)
        assert again.job["status"] == "paused"
        assert deps.prepare_job.await_count == 1


async def test_current_access_and_session_checked_on_reuse(service_env):
    env = service_env
    async with env.service() as (service, deps):
        await ensure(daily(service, deps), env.user)
    async with env.factory() as session:
        await SqlUserRepository(session).save(replace(env.user, is_active=False))
        await session.commit()
    async with env.service() as (service, deps):
        with pytest.raises((Forbidden, Unauthenticated)):
            await ensure(daily(service, deps), env.user)
        with pytest.raises(Unauthenticated):
            await daily(service, deps).ensure(
                env.user, RequestContext(), check_session=AsyncMock(side_effect=Unauthenticated())
            )


async def test_discard_cannot_erase_daily_marker_and_trigger_paid_repeat(service_env):
    env = service_env
    async with env.service() as (service, deps):
        first = await ensure(daily(service, deps), env.user)
        await service.pause(env.user, first.job["id"], check_session=AsyncMock())
        with pytest.raises(InvalidRequest, match="24-hour refresh"):
            await service.discard(env.user, first.job["id"], check_session=AsyncMock())
        again = await ensure(daily(service, deps), env.user)
        assert again.job["id"] == first.job["id"] and again.job["status"] == "paused"
        assert deps.prepare_job.await_count == 1
    after = SimpleNamespace(now=lambda: NOW + timedelta(hours=24))
    async with env.service(clock=after) as (service, deps):
        await service.discard(env.user, first.job["id"], check_session=AsyncMock())
        next_day = await ensure(daily(service, deps), env.user)
        assert next_day.job["id"] != first.job["id"]


@pytest.mark.parametrize("status", ["paused", "failed", "completed", "needs_review"])
def test_daily_marker_retention_includes_completed_failed_and_midnight_preparation(status):
    stored = job(status=status)
    previous_date_key = briefing_key(stored.owner_id, NOW - timedelta(days=1))
    stored = replace(stored, request_key=previous_date_key)
    assert retains_daily_admission(stored, NOW + timedelta(hours=23))
    assert not retains_daily_admission(stored, NOW + timedelta(hours=24))
    assert not retains_daily_admission(job(status=status), NOW)
