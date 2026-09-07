"""HTTP area launch resolves an immutable map and preserves its chosen interval."""

import json

from ase.application.research.service import ResearchCollectionService
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from test_area_report_generation import SpatialFixture
from test_map_research_origin import setup
from test_map_research_preview import headers
from test_saved_map_views import revise


async def test_http_area_report_uses_exact_saved_revision_and_historical_interval(
    client, container, user
):
    parent, claims, view, revision, _ = await setup(client, container, user)
    await revise(container, claims, view, revision)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    provider = SpatialFixture(True)
    container.research = ResearchCollectionService(lambda query: [provider])
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    body = {
        "template": "ask",
        "question": "Which observations cover this area?",
        "research_mode": "quick",
        "research_terms": ["area records"],
        "map_view_id": str(view.id),
        "map_revision_id": str(revision.id),
        "disclose_area_to_provider": True,
        "research_since": "2020-01-01T12:00:00.123456+02:00",
        "research_until": "2020-01-01T14:00:00.654321+02:00",
    }
    auth = await headers(client, user)
    response = await client.post("/api/reports", json=body, headers=auth)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["report"]["id"] != str(parent.id)
    assert result["report"]["scope"]["map_origin"]["revision_id"] == str(revision.id)
    assert result["version"]["period_from"].startswith("2020-01-01T10:00:00.123456")
    assert result["version"]["period_to"].startswith("2020-01-01T12:00:00.654321")
    assert len(result["version"]["evidence"]) == 3
    assert all(item["published_at"] is None for item in result["version"]["evidence"])
    assert provider.queries[0].since.year == 2020
    assert provider.queries[0].until.microsecond == 654321
    provider.queries.clear()
    denied = await client.post(
        "/api/reports", json={**body, "disclose_area_to_provider": False}, headers=auth
    )
    assert denied.status_code == 422
    assert provider.queries == []

    followup = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            "parent_report_id": result["report"]["id"],
        },
        headers=auth,
    )
    assert followup.status_code == 422
    assert "area research" in followup.text.lower()
    assert provider.queries == []
