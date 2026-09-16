"""Separate economy admission, retained markers and a bounded non-advisory request."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.application.daily_briefing import DailyBriefingService
from ase.application.dto import RequestContext
from ase.application.economy_briefing import COVERAGE_NOTE, economy_briefing_request
from ase.domain.daily_briefing import briefing_key, economy_briefing_key, retains_daily_admission
from ase.domain.economy_news import ECONOMIC_NEWS_IDS
from ase.domain.errors import InvalidRequest
from ase.domain.events import Category
from ase.domain.research import ResearchMode
from report_job_helpers import NOW, job
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401


def test_economy_request_is_one_deep_global_report_with_named_country_sections():
    request = economy_briefing_request()
    assert request.research_mode is ResearchMode.DETAILED
    assert request.report_style == "assessment"
    assert len(request.question) <= 2000
    assert request.categories == (Category.ECONOMIC,) and request.window_hours == 48
    # One research source per reviewed economic feed, whatever the catalogue holds today.
    assert len(request.research_source_ids) == len(ECONOMIC_NEWS_IDS)
    assert len(request.research_terms) <= 12
    assert request.team_id is None and not request.research_web_search
    for phrase in (
        "United Kingdom",
        "United States",
        "Russia",
        "China",
        "Iran",
        "in-text citations",
        "observation periods",
        "missing or stale",
        "buy/sell",
        "Cross-country comparison",
        "same indicator, units and observation year",
        "percentage-point changes",
        "do not infer causation from correlation",
        "central government debt",
        "gross capital formation",
        "Coverage and method",
    ):
        assert phrase in request.question


async def test_economic_daily_job_separate_from_live_monitor_and_cannot_be_discarded(service_env):
    env = service_env
    async with env.service() as (jobs, deps):
        normal = DailyBriefingService(jobs, deps.repo, deps.uow, deps.clock, asyncio.Lock())
        economic = DailyBriefingService(
            jobs,
            deps.repo,
            deps.uow,
            deps.clock,
            asyncio.Lock(),
            identity=economy_briefing_key,
            request_factory=economy_briefing_request,
            coverage_note=COVERAGE_NOTE,
        )
        first = await normal.ensure(env.user, RequestContext(), check_session=AsyncMock())
        second = await economic.ensure(env.user, RequestContext(), check_session=AsyncMock())
        again = await economic.ensure(env.user, RequestContext(), check_session=AsyncMock())
        assert first.job["id"] != second.job["id"] == again.job["id"]
        assert second.coverage_note == COVERAGE_NOTE
        assert second.next_refresh_at == NOW + timedelta(hours=24)
        await jobs.pause(env.user, second.job["id"], check_session=AsyncMock())
        with pytest.raises(InvalidRequest, match="24-hour refresh"):
            await jobs.discard(env.user, second.job["id"], check_session=AsyncMock())
        paused = await economic.ensure(env.user, RequestContext(), check_session=AsyncMock())
        assert paused.job["status"] == "paused" and deps.prepare_job.await_count == 2


@pytest.mark.parametrize("status", ["completed", "needs_review", "failed", "paused"])
def test_economic_marker_survives_midnight_and_expires_after_24_hours(status):
    stored = job(status=status)
    key = economy_briefing_key(stored.owner_id, NOW - timedelta(days=1))
    stored = replace(stored, request_key=key)
    assert key != briefing_key(stored.owner_id, NOW - timedelta(days=1))
    assert retains_daily_admission(stored, NOW + timedelta(hours=23))
    assert not retains_daily_admission(stored, NOW + timedelta(hours=24))
