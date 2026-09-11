"""New source capabilities remain bounded, controllable and honestly attributed."""

from dataclasses import replace

import httpx
import pytest

from ase.adapters.research.publisher import PUBLISHER_SEEDS
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.grading import profiles_from_specs
from ase.container.research import research_service
from ase.container.research_sources import research_source_specs
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_tasks import PlannedQueryTask
from ase.domain.source_controls import source_control_keys
from hazard_area_helpers import QUERY as AREA_QUERY
from research_feed_helpers import CLOCK, QUERY, PublicFeed, rss


@pytest.mark.parametrize(
    "focus", [ResearchFocus.GENERAL, ResearchFocus.COMPANY, ResearchFocus.DOMAIN]
)
@pytest.mark.parametrize("spatial", [False, True])
async def test_all_languages_fit_provider_bound_without_silent_truncation(
    monkeypatch, focus, spatial
):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    query = replace(
        AREA_QUERY if spatial else QUERY,
        focus=focus,
        subject="CIK:123456" if focus is ResearchFocus.COMPANY else "example.com",
        languages=("en", "ru", "zh", "fa", "de", "fr", "es", "ar"),
        mode=ResearchMode.DETAILED,
    )
    service = research_service(feed.http, CLOCK, retained_store=InMemoryEventStore())
    try:
        plan = service.plan(query)
        ids = [task.source_id for task in plan.tasks]
        assert len(ids) <= 64 and len(ids) == len(set(ids))
        if spatial:
            assert ids[:4] == [
                "research-usgs-area",
                "research-eonet-area",
                "research-openaq-area",
                "research-retained-area-feeds",
            ]
            assert not any(id_.startswith("research_publisher_") for id_ in ids)
        else:
            assert {f"research_publisher_{seed.spec.id}" for seed in PUBLISHER_SEEDS} <= set(ids)
            assert "research-usgs-area" not in ids
        assert not feed.requests  # Preview never performs source requests.
    finally:
        await feed.http.aclose()


@pytest.mark.parametrize(
    ("parent", "capability"),
    [
        ("usgs_earthquakes", "research-usgs-area"),
        ("nasa_eonet", "research-eonet-area"),
        ("bbc_world", "research_publisher_bbc_world"),
    ],
)
async def test_environment_parent_disables_new_catalogue_and_research(
    monkeypatch, parent, capability
):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    try:
        query = QUERY if "publisher" in capability else AREA_QUERY
        plan = research_service(feed.http, CLOCK, (parent,)).plan(query)
        assert capability not in {task.source_id for task in plan.tasks}
        assert capability not in {spec.id for spec in research_source_specs((parent,))}
        assert source_control_keys(capability) == (capability, parent)
    finally:
        await feed.http.aclose()


def test_publisher_derivatives_do_not_gain_independent_organisation_identity():
    specs = research_source_specs()
    profiles = profiles_from_specs((*specs, *(seed.spec for seed in PUBLISHER_SEEDS)))
    for seed in PUBLISHER_SEEDS:
        assert profiles[f"research_publisher_{seed.spec.id}"].independence_key == (
            profiles[seed.spec.id].independence_key
        )


async def test_default_plan_interleaves_official_outlet_regional_and_social(monkeypatch):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    try:
        plan = research_service(feed.http, CLOCK).plan(QUERY)
        feeds = [
            task.source_id
            for task in plan.tasks
            if task.source_id.startswith(
                ("research_publisher_", "research_regional_", "research_social_")
            )
        ]
        assert feeds[0] == "research_publisher_gov_uk_fcdo_news"
        assert feeds[1] == "research_publisher_bbc_world"
        assert feeds[2].startswith("research_regional_")
        assert feeds[3].startswith("research_social_")
        assert plan.request_limit == 6
    finally:
        await feed.http.aclose()


@pytest.mark.parametrize("explicit", [True, False])
async def test_saved_company_tasks_survive_larger_catalogue(monkeypatch, explicit):
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss("")))
    source = "research_google_news_en"
    tasks = tuple(
        PlannedQueryTask(str(i), source, "challenge", (f"question {i}",)) for i in range(8)
    )
    query = replace(
        QUERY,
        focus=ResearchFocus.COMPANY,
        subject="CIK:123456",
        languages=("en", "ru", "zh", "fa", "de", "fr", "es", "ar"),
        source_ids=(source,) if explicit else None,
        planned_tasks=tasks,
    )
    try:
        plan = research_service(feed.http, CLOCK).plan(query)
        assert len(plan.tasks) <= 64
        assert {row.task_id for row in plan.tasks if row.purpose != "baseline"} == {
            f"operator:{i}" for i in range(8)
        }
        assert plan.request_limit == 6
        assert not feed.requests
    finally:
        await feed.http.aclose()
