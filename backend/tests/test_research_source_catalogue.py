"""Research capability context survives source listing and saved report generation."""

import json
from dataclasses import replace
from datetime import timedelta

from httpx import AsyncClient

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.news import EDITIONS
from ase.adapters.research.publisher import PUBLISHER_SEEDS
from ase.application.feeds.grading import profiles_from_specs
from ase.container import Container
from ase.container.research_sources import research_source_specs
from ase.domain.events import Reliability
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_plan import ResearchPlan
from ase.domain.users import User
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body


def test_catalogue_covers_exact_provider_and_private_event_ids_without_assessment_claims():
    specs = research_source_specs()
    expected = {
        *(f"research_google_news_{language}" for language in EDITIONS),
        *(f"research_regional_{seed.spec.id}" for seed in REGIONAL_SEEDS),
        *(f"research_publisher_{seed.spec.id}" for seed in PUBLISHER_SEEDS),
        "research-usgs-area",
        "research-eonet-area",
        "research-openaq-area",
        "research-web-search",
        "research-sec-submissions",
        "research-sec-company-directory",
        "research-companies-house",
        "research-companies-house-officers",
        "research-companies-house-psc",
        "research-gleif-profile",
        "research-gleif-direct-parent",
        "research-gleif-ultimate-parent",
        "research-openalex",
        "research-crossref",
        "research-world-bank",
        "research-ons-cpih",
        "research-ecb-gbp-reference-rate",
        "research-ioda-outage-events",
        "research-cloudflare-radar-layer3",
        "research-cloudflare-radar-layer7",
        "research-uk-parliament",
        "research-ooni-aggregate",
        "research-copernicus-footprints",
        "research-retained-area-feeds",
        "research-contracts-finder",
        "research-aiddata-projects",
        "research-designations-uksl",
        "research-designations-ofac_sdn",
        "research-rdap",
        "research-youtube",
        "research-certificate-transparency",
        "research_import",
        "research_media",
        "research-dns-a",
        "research-dns-aaaa",
        "research-dns-mx",
        "research-dns-ns",
    }
    assert {spec.id for spec in specs} == expected
    assert len(specs) == len(expected)
    for spec in specs:
        assert spec.reliability is Reliability.F
        assert spec.rating is not None
        assert spec.rating.status == "unassessed" and spec.rating.assessed_grade is None
        assert spec.rating.reviewed_at is None and not spec.rating.publisher_reliability_assessed
        assert spec.rating.basis != "No source-specific reliability assessment basis is recorded."
        assert spec.rating.scope and len(spec.rating.limitations) >= 3
        assert not spec.url and not spec.homepage
    assert {spec.id for spec in specs if spec.requires_key} == {
        "research-web-search",
        "research-openaq-area",
        "research-companies-house",
        "research-cloudflare-radar-layer3",
        "research-cloudflare-radar-layer7",
        "research-companies-house-officers",
        "research-companies-house-psc",
        "research-certificate-transparency",
        "research-youtube",
    }


def test_disabled_parent_feeds_and_individual_capabilities_are_excluded():
    disabled = (
        GOOGLE_NEWS.id,
        REGIONAL_SEEDS[0].spec.id,
        "research-dns-a",
        "research_media",
        f"research_regional_{REGIONAL_SEEDS[1].spec.id}",
    )
    ids = {spec.id for spec in research_source_specs(disabled)}
    assert not any(id_.startswith("research_google_news_") for id_ in ids)
    assert f"research_regional_{REGIONAL_SEEDS[0].spec.id}" not in ids
    assert f"research_regional_{REGIONAL_SEEDS[1].spec.id}" not in ids
    assert "research-dns-a" not in ids and "research_media" not in ids
    assert "research-dns-aaaa" in ids and "research_import" in ids
    remaining = research_source_specs(("research_google_news_fr",))
    assert "research_google_news_en" in {spec.id for spec in remaining}
    assert "research_google_news_fr" not in {spec.id for spec in remaining}


def test_unknown_origins_do_not_gain_independence_from_edition_or_platform_names():
    profiles = profiles_from_specs(research_source_specs())
    for id_, profile in profiles.items():
        if id_.startswith("research_google_news_") or id_ in {
            "research_import",
            "research_media",
        }:
            assert profile.independence_key == ""
    assert profiles["research-sec-submissions"].independence_key == (
        profiles["research-sec-company-directory"].independence_key
    )
    assert len({p.independence_key for id_, p in profiles.items() if "research-dns-" in id_}) == 1


async def test_api_combines_live_and_research_without_urls_or_secrets(
    client: AsyncClient,
    container: Container,
    user: User,
):
    original = container.research_sources
    container.research_sources = tuple(
        replace(spec, url="https://fixture.invalid/?key=NEVER_EXPOSE", homepage="SECRET_HOME")
        for spec in original
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/sources", headers=bearer(token))
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    # Keyed feeds that are not built without a credential still appear, so the
    # inventory is complete; they carry a "key missing" connection rather than health.
    assert {item["id"] for item in items} == {
        *(spec.id for spec in original),
        *(connector.spec.id for connector in container.connectors),
        *(spec.id for spec in container.optional_connector_specs()),
    }
    assert len(items) == len({item["id"] for item in items})
    assert items == sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))
    assert "NEVER_EXPOSE" not in response.text and "SECRET_HOME" not in response.text
    for item in items:
        assert set(item) == {
            "id",
            "name",
            "organisation",
            "parent_organisation",
            "category",
            "language",
            "reliability",
            "rating",
            "kind",
            "requires_key",
            "collection_mode",
            "coverage_scope",
            "coverage_countries",
            "coverage_regions",
            "coverage_note",
            "connection",
        }
    assert next(item for item in items if item["id"] == "research_media")["rating"]["basis"]


class CatalogueResearch:
    def plan(self, query: ResearchQuery) -> ResearchPlan:
        return ResearchPlan(
            query.question, query.since, query.until, query.languages, (), 6, 45, 200
        )

    async def collect(self, query: ResearchQuery, *, replan=None) -> ResearchBatch:
        ids = ("research_google_news_fr", "research_import", "research_media")
        return ResearchBatch(
            tuple(
                make_event(
                    f"catalogue-{index}",
                    source_id=id_,
                    title=f"Collected finding {index}",
                    published_at=query.until - timedelta(hours=1),
                ).with_changes(reliability=Reliability.F)
                for index, id_ in enumerate(ids)
            ),
            (
                CollectionAttempt(
                    "fixture",
                    "Synthetic collection",
                    CollectionStatus.COMPLETED,
                    3,
                    "Synthetic source context only.",
                    "fr",
                ),
            ),
        )


async def test_saved_report_freezes_source_specific_basis_from_composed_profiles(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
):
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    container.research = CatalogueResearch()
    container.llm = ScriptedGateway(
        json.dumps(
            {
                "pir": "What changed?",
                "sirs": ["Reporting"],
                "eeis": [],
                "search_terms": ["finding"],
                "categories": ["news"],
            }
        ),
        json.dumps(good_body()),
    )
    response = await client.post(
        "/api/reports",
        json={
            "template": "ask",
            "question": "What changed?",
            "research_mode": "quick",
            "research_languages": ["fr"],
        },
        headers=bearer(user_token),
    )
    assert response.status_code == 201, response.text
    evidence = response.json()["version"]["evidence"]
    assert len(evidence) == 3
    for item in evidence:
        profile = container.source_profiles[item["source_id"]]
        assert item["source_rating"]["basis"] == profile.rating.basis
        assert item["source_rating"]["status"] == "unassessed"
        container.source_profiles[item["source_id"]] = replace(
            profile,
            rating=replace(profile.rating, basis="Later catalogue context."),
        )
    report_id = response.json()["report"]["id"]
    saved = await client.get(f"/api/reports/{report_id}", headers=bearer(user_token))
    assert saved.status_code == 200
    assert saved.json()["version"]["evidence"] == evidence
    assert container.store.get("catalogue-0") is None
