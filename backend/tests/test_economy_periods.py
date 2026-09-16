"""Selectable economic windows remain separate, bounded and protected on every status."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.application.daily_briefing import DailyBriefingService
from ase.application.dto import RequestContext
from ase.application.economy_briefing import economy_briefing_request
from ase.application.feeds.budgets import budget_for
from ase.domain.daily_briefing import economy_briefing_key, retains_daily_admission
from ase.domain.economy_periods import EconomyWindowDays, economy_window
from ase.domain.errors import InvalidRequest
from ase.domain.events import Category
from feeds_helpers import NOW as NEWS_NOW
from report_job_helpers import NOW, job
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from test_economy_news import news, service


def briefing(jobs, deps, days, guard=None):
    return DailyBriefingService(
        jobs,
        deps.repo,
        deps.uow,
        deps.clock,
        guard or asyncio.Lock(),
        identity=lambda owner_id, at: economy_briefing_key(owner_id, at, days),
        request_factory=lambda: economy_briefing_request(days),
    )


@pytest.mark.parametrize("days", EconomyWindowDays)
def test_every_summary_requests_and_names_its_actual_window(days):
    request = economy_briefing_request(days)
    assert request.window_hours == int(days) * 24
    assert f"{int(days)} day economic summary" in request.question
    assert "exact supplied reporting range" in request.question
    assert "concise executive paragraph" in request.question
    assert "short takeaway paragraph" in request.question
    assert "not an unspecified timeframe" in request.question
    assert len(request.question) <= 2000


@pytest.mark.parametrize("days", [0, 1, 3, 6, 15, 30, True, "2", 2.0])
def test_only_explicit_supported_windows_are_admitted(days):
    with pytest.raises(ValueError):
        economy_window(days)


@pytest.mark.parametrize("days", EconomyWindowDays)
@pytest.mark.parametrize("status", ["completed", "needs_review", "failed", "paused"])
def test_every_window_retains_its_daily_marker_across_midnight(days, status):
    stored = job(status=status)
    stored = replace(
        stored,
        request_key=economy_briefing_key(stored.owner_id, NOW - timedelta(days=1), days),
    )
    assert retains_daily_admission(stored, NOW + timedelta(hours=23))
    assert not retains_daily_admission(stored, NOW + timedelta(hours=24))


async def test_windows_and_owners_are_isolated_and_paused_work_is_not_recreated(service_env):
    env = service_env
    async with env.service() as (jobs, deps):
        results = {}
        for days in EconomyWindowDays:
            selected = briefing(jobs, deps, days)
            first = await selected.ensure(env.user, RequestContext(), check_session=AsyncMock())
            results[days] = first.job["id"]
            await jobs.pause(env.user, first.job["id"], check_session=AsyncMock())
            with pytest.raises(InvalidRequest, match="24-hour refresh"):
                await jobs.discard(env.user, first.job["id"], check_session=AsyncMock())
            again = await selected.ensure(env.user, RequestContext(), check_session=AsyncMock())
            assert again.job["id"] == first.job["id"] and again.job["status"] == "paused"
        assert len(set(results.values())) == 4 and deps.prepare_job.await_count == 4
        other = await briefing(jobs, deps, EconomyWindowDays.TWO).ensure(
            env.stranger, RequestContext(), check_session=AsyncMock()
        )
        assert other.job["id"] not in results.values()
    next_clock = SimpleNamespace(now=lambda: NOW + timedelta(hours=23))
    async with env.service(clock=next_clock) as (jobs, deps):
        again = await briefing(jobs, deps, EconomyWindowDays.FOURTEEN).ensure(
            env.user, RequestContext(), check_session=AsyncMock()
        )
        assert again.job["id"] == results[EconomyWindowDays.FOURTEEN]
        deps.prepare_job.assert_not_awaited()
    next_clock = SimpleNamespace(now=lambda: NOW + timedelta(hours=24))
    async with env.service(clock=next_clock) as (jobs, deps):
        fresh = await briefing(jobs, deps, EconomyWindowDays.FOURTEEN).ensure(
            env.user, RequestContext(), check_session=AsyncMock()
        )
        assert fresh.job["id"] not in results.values()


@pytest.mark.parametrize("days", EconomyWindowDays)
async def test_headline_publication_range_is_half_open_and_undated_items_are_not_backfilled(days):
    boundary = NEWS_NOW - timedelta(days=days)
    rows = (
        news("boundary", title="Inflation report at start", published_at=boundary),
        news("older", title="Inflation report before start", published_at=boundary - timedelta(microseconds=1)),
        news("end", title="Inflation report before end", published_at=NEWS_NOW - timedelta(microseconds=1)),
        news("at-end", title="Inflation report at end", published_at=NEWS_NOW),
        news("future", title="Inflation report after end", published_at=NEWS_NOW + timedelta(seconds=1)),
        news("undated", title="Inflation report with no publication date", published_at=None),
    )
    selected, _ = service(rows)
    result = await selected.read(days=days)
    assert {item.id for item in result.items} == {rows[0].id, rows[2].id}
    assert result.as_of == NEWS_NOW and result.window_hours == int(days) * 24
    assert f"selected {int(days)} days" in result.coverage_note
    assert "may not retain the entire selected period" in result.coverage_note


async def test_wider_window_adds_retained_older_news_and_disabled_sources_stay_empty():
    rows = tuple(
        news(
            str(day), title=f"Inflation report published {day} days ago", published_at=NEWS_NOW - timedelta(days=day)
        )
        for day in (1, 4, 6, 13)
    )
    selected, _ = service(rows)
    for days, count in zip(EconomyWindowDays, (1, 2, 3, 4), strict=True):
        assert len((await selected.read(days=days)).items) == count
    disabled, _ = service(rows, disabled=("economic_bbc_business",))
    result = await disabled.read(days=EconomyWindowDays.FOURTEEN)
    assert not result.items and result.window_hours == 336


def test_retention_can_cover_fourteen_days_without_increasing_the_item_budget():
    budget = budget_for(Category.ECONOMIC)
    assert budget.window == timedelta(days=14) and budget.max_items == 5000
