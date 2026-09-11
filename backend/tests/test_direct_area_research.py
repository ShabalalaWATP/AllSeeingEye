"""A dashboard boundary starts private research without a pre-existing report."""

import copy
import json
import math
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ase.api.schemas_research_area import ResearchAreaIn
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import template_for
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import NotFound
from ase.domain.research import ResearchMode
from ase.domain.research_area import ResearchArea
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from team_helpers import CONTEXT, team_service
from test_area_report_generation import SpatialFixture
from test_map_research_origin import AREA
from test_map_research_preview import headers
from test_report_team_scope import team_for
from test_research_plan import NOW


def area_input():
    return {"geometry": AREA.to_collection()}


def preview_body():
    return {
        "question": "Which observations cover this area?",
        "since": (NOW - timedelta(hours=24)).isoformat(),
        "until": NOW.isoformat(),
        "research_area": area_input(),
    }


def report_body():
    return {
        "template": "ask",
        "question": "Which observations cover this area?",
        "research_mode": "quick",
        "research_terms": ["area records"],
        "research_area": area_input(),
        "disclose_area_to_provider": True,
        "research_since": (NOW - timedelta(hours=24)).isoformat(),
        "research_until": NOW.isoformat(),
    }


def test_direct_area_input_canonicalises_without_trusting_a_supplied_hash():
    data = area_input()
    parsed = ResearchAreaIn.model_validate(data)
    assert parsed.to_domain() == ResearchArea(AREA)
    data["geometry"]["features"].clear()
    assert parsed.to_domain().geometry == AREA
    with pytest.raises(ValidationError):
        ResearchAreaIn.model_validate({**area_input(), "sha256": "a" * 64})


@pytest.mark.parametrize(
    "change", ["point", "unclosed", "self_crossing", "too_large", "too_many_vertices", "non_finite"]
)
def test_direct_area_input_rejects_invalid_or_excessive_geometry(change):
    value = area_input()
    geometry = value["geometry"]["features"][0]["geometry"]
    if change == "point":
        geometry.update(type="Point", coordinates=[0, 50])
    elif change == "unclosed":
        geometry["coordinates"][0].pop()
    elif change == "self_crossing":
        geometry["coordinates"] = [[[0, 50], [1, 51], [1, 50], [0, 51], [0, 50]]]
    elif change == "too_large":
        value["geometry"]["ignored"] = "x" * (16 * 1024)
    elif change == "too_many_vertices":
        ring = [
            [round(math.cos(i / 257 * math.tau), 5), round(50 + math.sin(i / 257 * math.tau), 5)]
            for i in range(257)
        ]
        geometry["coordinates"] = [[*ring, ring[0]]]
    else:
        geometry["coordinates"][0][0][0] = float("nan")
    with pytest.raises(ValidationError):
        ResearchAreaIn.model_validate(value)


def test_direct_area_roundtrips_exact_scope_and_fixed_interval():
    request = ReportRequest(
        "ask",
        question="What is happening?",
        research_mode=ResearchMode.QUICK,
        research_area=ResearchArea(AREA),
        disclose_area_to_provider=True,
        research_since=NOW - timedelta(hours=24),
        research_until=NOW,
    )
    assert request.effective_area == ResearchArea(AREA)
    scope = report_scope(request, template_for("ask"))
    assert scope["research_area"]["sha256"] == AREA.sha256
    assert ReportRequest.from_scope("ask", scope) == request
    with pytest.raises(ValueError):
        replace(request, map_view_id=uuid4(), map_revision_id=uuid4())
    damaged = copy.deepcopy(scope)
    damaged["research_area"]["sha256"] = "a" * 64
    with pytest.raises(ValueError):
        ReportRequest.from_scope("ask", damaged)


async def test_direct_preview_is_local_and_has_no_saved_origin(
    client, container, user, monkeypatch
):
    collect = AsyncMock(side_effect=AssertionError("Preview must not collect"))
    monkeypatch.setattr(container.research, "collect", collect)
    response = await client.post(
        "/api/research/runs/plan", json=preview_body(), headers=await headers(client, user)
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["area"]["sha256"] == AREA.sha256
    assert result["map_origin"] is None
    assert result["model_calls"] == 0
    assert response.headers["cache-control"] == "no-store"
    collect.assert_not_awaited()


@pytest.mark.parametrize(
    "change",
    [
        {"map_view_id": str(uuid4()), "map_revision_id": str(uuid4())},
        {"country_iso": "GB"},
        {"focus": "company"},
    ],
)
async def test_direct_preview_rejects_ambiguous_scope(client, user, change):
    response = await client.post(
        "/api/research/runs/plan",
        json={**preview_body(), **change},
        headers=await headers(client, user),
    )
    assert response.status_code == 422


async def test_direct_preview_rejects_foreign_team(client, user):
    response = await client.post(
        "/api/research/runs/plan",
        json={**preview_body(), "team_id": str(uuid4())},
        headers=await headers(client, user),
    )
    assert response.status_code == 404


async def test_direct_report_preserves_area_on_regeneration_and_blocks_unscoped_followup(
    client, container, user, clock
):
    clock.advance(NOW - clock.now())
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    provider = SpatialFixture(True)
    container.research = ResearchCollectionService(lambda query: [provider])
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    auth = await headers(client, user)
    response = await client.post("/api/reports", json=report_body(), headers=auth)
    assert response.status_code == 201, response.text
    result = response.json()
    report_id = result["report"]["id"]
    assert result["report"]["scope"]["research_area"]["sha256"] == AREA.sha256
    assert "map_origin" not in result["report"]["scope"]
    assert result["version"]["research"]["plan"]["area"]["sha256"] == AREA.sha256
    assert len(result["version"]["evidence"]) == 3
    assert all(item["source_id"] == provider.id for item in result["version"]["evidence"])
    assert provider.queries[0].area == ResearchArea(AREA)
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    regenerated = await client.post(f"/api/reports/{report_id}/versions", headers=auth)
    assert regenerated.status_code == 201, regenerated.text
    assert regenerated.json()["report"]["scope"] == result["report"]["scope"]
    assert provider.queries[-1].area == ResearchArea(AREA)
    assert provider.queries[-1].since == provider.queries[0].since
    followup = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            "parent_report_id": report_id,
        },
        headers=auth,
    )
    assert followup.status_code == 422
    assert "area research" in followup.text.lower()


async def test_direct_report_requires_disclosure_before_collection(client, container, user):
    provider = SpatialFixture()
    container.research = ResearchCollectionService(lambda query: [provider])
    response = await client.post(
        "/api/reports",
        json={**report_body(), "disclose_area_to_provider": False},
        headers=await headers(client, user),
    )
    assert response.status_code == 422
    assert provider.queries == []


async def test_direct_area_authorisation_rechecks_team_membership_after_collection(
    container, user, admin
):
    team = await team_for(container, admin, user)
    request = ReportRequest(
        "ask",
        question="Area records?",
        research_mode=ResearchMode.QUICK,
        research_area=ResearchArea(AREA),
        disclose_area_to_provider=True,
        team_id=team.id,
    )
    async with container.session_factory() as session:
        repos = container.repositories(session)
        service = ReportAuthorisation(
            container.access_policy(session),
            repos.reports,
            repos.plans,
            repos.aois,
            repos.uow,
        )
        await service.prepare(user, request)
        await repos.uow.rollback()
        async with team_service(container) as teams:
            await teams.remove_member(admin, team.id, user.id, CONTEXT)
        with pytest.raises(NotFound):
            await service.finish(user, request, None, None)


async def test_direct_preview_rejects_interval_beyond_two_years(client, user):
    response = await client.post(
        "/api/research/runs/plan",
        json={**preview_body(), "since": (NOW - timedelta(days=731)).isoformat()},
        headers=await headers(client, user),
    )
    assert response.status_code == 422
