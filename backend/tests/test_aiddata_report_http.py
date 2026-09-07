"""Historical project requests traverse real catalogue composition and persistence."""

import json
from dataclasses import replace
from uuid import UUID

import pytest

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.container.research import research_service
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from team_helpers import CONTEXT
from test_aiddata_search import END, START, catalogue
from test_map_research_preview import headers
from test_report_team_scope import save_team_report
from test_research_area import area
from test_saved_map_views import STATE, claims_for, create, revise


@pytest.mark.parametrize("disabled", [False, True])
@pytest.mark.parametrize("saved_area", [False, True])
async def test_historical_http_report_and_regeneration_preserve_project_records(
    client, container, user, admin, tmp_path, disabled, saved_area
):
    map_ids = {}
    if saved_area:
        parent = await save_team_report(container, user, None)
        claims = await claims_for(client, container, user)
        geometry = area([[[0, 0], [1, 0], [1, 1], [0, 0]]]).geometry
        view, revision = await create(container, claims, parent.id, replace(STATE, aoi=geometry))
        map_ids = {"map_view_id": str(view.id), "map_revision_id": str(revision.id)}
        # A later revision cannot redirect this explicitly chosen area.
        await revise(container, claims, view, revision)
    container.research = research_service(
        container.http,
        container.clock,
        admission=container.source_admission,
        countries=container.countries,
        aiddata_catalogue_path=str(catalogue(tmp_path)),
    )
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    if disabled:
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set(
                "research-aiddata-projects", False, container.clock.now(), admin.id
            )
            await session.commit()
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    auth = await headers(client, user)
    preview = await client.post(
        "/api/research/runs/plan",
        headers=auth,
        json={
            **map_ids,
            "question": "Airport project commitments",
            "country_iso": None if saved_area else "LA",
            "source_ids": ["research-aiddata-projects"],
            "terms": ["airport"],
            "time_basis": "recorded_time",
            "since": START.isoformat(),
            "until": END.isoformat(),
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["time_basis"] == "recorded_time"
    if not disabled:
        assert any(task["selected"] and task["supported"] for task in preview.json()["tasks"])
    response = await client.post(
        "/api/reports",
        headers=auth,
        json={
            **map_ids,
            "disclose_area_to_provider": saved_area,
            "template": "ask",
            "question": "Airport project commitments",
            "country": None if saved_area else "LA",
            "research_mode": "quick",
            "research_source_ids": ["research-aiddata-projects"],
            "research_terms": ["airport"],
            "research_time_basis": "recorded_time",
            "research_since": START.isoformat(),
            "research_until": END.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    evidence = result["version"]["evidence"]
    if disabled:
        assert evidence == []
        assert container.store.stats().total == 0
        return
    assert len(evidence) == 1, result["version"].get("research")
    item = evidence[0]
    assert item["project"]["commitment_year"] == 2011
    assert item["published_at"] is None and item["geometry"] is not None
    assert {row["key"]: row["value"] for row in item["attributes"]}[
        "aiddata_amount_constant_usd_2021"
    ] == "123.5"
    assert result["report"]["scope"]["research_time_basis"] == "recorded_time"
    assert container.store.stats().total == 0
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    async with container.session_factory() as session:
        _, second = await container.generate_report(session).regenerate(
            user,
            UUID(result["report"]["id"]),
            CONTEXT,
        )
    assert second.period_from == START and second.period_to == END
    assert second.evidence[0].project.project_id == item["project"]["project_id"]
    assert second.evidence[0].published_at is None
    if saved_area:
        assert second.research.plan.area.geometry == geometry
        assert result["report"]["scope"]["map_origin"]["revision_id"] == map_ids["map_revision_id"]
    followup = await client.post(
        "/api/reports",
        headers=auth,
        json={
            "template": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            "parent_report_id": result["report"]["id"],
        },
    )
    assert followup.status_code == 422
    assert "historical" in followup.text.lower()
