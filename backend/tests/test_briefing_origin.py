"""Automatic workspace briefings carry a trusted, server-assigned origin (KAN-87)."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, Mock

import pytest

from ase.api.schemas_reports import ReportCreateIn
from ase.application.cyber_briefing import cyber_briefing_request
from ase.application.daily_briefing import DailyBriefingService, briefing_request
from ase.application.dto import RequestContext
from ase.application.economy_briefing import economy_briefing_request
from ase.application.report_jobs.listing import JobListQuery
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_origin, report_scope
from ase.application.reports.templates import TEMPLATES
from ase.domain.reports import ReportOrigin
from ase.domain.research import ResearchFocus, ResearchMode
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import frozen
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from test_report_listing import seed_reports


@pytest.mark.parametrize(
    ("request_factory", "kind"),
    [
        (briefing_request, "daily"),
        (economy_briefing_request, "economy"),
        (cyber_briefing_request, "cyber"),
    ],
)
def test_workspace_briefings_are_classified_by_the_server(request_factory, kind):
    request = request_factory()
    scope = report_scope(request, TEMPLATES[request.template_id])
    assert request.briefing == kind
    assert report_origin(request) == ReportOrigin.BRIEFING == scope["origin"]
    assert scope["briefing"] == kind
    restored = ReportRequest.from_scope(request.template_id, scope)
    assert restored.briefing == kind
    assert report_scope(restored, TEMPLATES[request.template_id]) == scope


def test_requested_subscription_and_geolocation_origins_are_unchanged():
    research = ReportRequest(template_id="ask", question="What changed?")
    scope = report_scope(research, TEMPLATES["ask"])
    assert scope["origin"] == "research" and "briefing" not in scope
    assert report_origin(replace(research, automation=True)) == "subscription"
    media = ReportRequest(
        template_id="ask",
        question="Where was this taken?",
        research_mode=ResearchMode.QUICK,
        research_focus=ResearchFocus.MEDIA,
    )
    assert report_origin(media) == "geolocation"


def test_briefing_kind_is_bounded_and_survives_background_execution():
    # Background execution marks every request as automation; the briefing origin stays.
    executing = replace(briefing_request(), automation=True)
    assert report_origin(executing) == "briefing"
    with pytest.raises(ValueError, match="briefing"):
        ReportRequest(template_id="ask", question="Daily", briefing="weekly")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="briefing"):
        ReportRequest.from_scope("ask", {"question": "Daily", "briefing": "weekly"})


def test_public_report_requests_cannot_claim_the_briefing_origin():
    claimed = {"template": "ask", "question": "x", "briefing": "daily", "origin": "briefing"}
    request = ReportCreateIn.model_validate(claimed).to_request()
    assert request.briefing is None and report_origin(request) == "research"


async def test_saved_research_omits_briefings_before_pagination(client, container, user):
    records = await seed_reports(
        container,
        user.id,
        [{"origin": "research"}] + [{"origin": "briefing", "briefing": "daily"}] * 3,
    )
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    research = (await client.get("/api/reports?origin=research&limit=1", headers=headers)).json()
    assert [row["id"] for row in research["items"]] == [str(records[0].id)]
    assert research["has_more"] is False
    briefings = (await client.get("/api/reports?origin=briefing", headers=headers)).json()
    assert [row["id"] for row in briefings["items"]] == [str(row.id) for row in records[:0:-1]]
    direct = await client.get(f"/api/reports/{records[1].id}", headers=headers)
    assert direct.status_code == 200


async def test_prepared_daily_briefing_job_is_hidden_from_default_progress(service_env):
    env = service_env

    def freeze(prepared, routing):
        # Production freezing keeps the prepared job's report scope unchanged.
        return frozen(prepared, routing) | {
            "scope": report_scope(prepared.request, prepared.template)
        }

    async with env.service(freeze=Mock(side_effect=freeze)) as (service, deps):
        daily = DailyBriefingService(service, deps.repo, deps.uow, deps.clock, asyncio.Lock())
        prepared = await daily.ensure(env.user, RequestContext(), check_session=AsyncMock())
        assert prepared.job["origin"] == "briefing"
        assert await service.list(env.user, 20, check_session=AsyncMock()) == []
        query = JobListQuery(include_briefings=True)
        shown, _ = await service.page(env.user, query, check_session=AsyncMock())
        assert [row["id"] for row in shown] == [prepared.job["id"]]
        hidden, _ = await service.page(env.stranger, query, check_session=AsyncMock())
        assert hidden == []
