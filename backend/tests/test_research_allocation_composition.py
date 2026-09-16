"""Production profile coverage and fail-closed E00 admission composition, with no live IO."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from ase.application.research.source_allocator import allocate_sources
from ase.application.source_capabilities import CapabilityReadiness
from ase.application.source_inventory import SourceRequirement
from ase.container import research_allocation as composition
from ase.container.research import research_service
from ase.container.research_allocation import compose_research_allocation, load_research_allocation
from ase.container.research_allocation_profiles import REVIEW_DATE, research_allocation_profiles
from ase.container.research_capabilities import research_capability_registry
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.source_capabilities import ContentCapability
from test_source_allocator import scenario

NEWS = "research_google_news_en"
PARLIAMENT = "research-uk-parliament"
CERT = "research-certificate-transparency"
NOW = datetime(2026, 9, 14, tzinfo=UTC)


def requirement(kind, satisfied, *, optional=False):
    return SourceRequirement(kind, satisfied, "environment", None, "Presence only", optional)


def test_every_executable_e00_provider_has_a_reviewed_profile():
    registry, profiles = research_capability_registry(), research_allocation_profiles()
    ids = tuple(key for key, cap in registry.capabilities.items() if cap.provider_id is not None)
    result = compose_research_allocation(ids, enabled=dict.fromkeys(ids, True))
    assert set(profiles) == set(ids) == {row.capability.id for row in result.resolved}
    # 140: one aggregated provider each for the curated Telegram and Bluesky sets, not
    # one per channel or account.
    assert len(ids) == 140
    assert result.profile_review_date == REVIEW_DATE
    assert all(row.review_note.startswith(REVIEW_DATE) for row in profiles.values())
    assert not {"research_import", "research_media", "research-web-search"} & set(profiles)
    for key, profile in profiles.items():
        cap = registry.capabilities[key]
        if cap.content is ContentCapability.DISCOVERY:
            assert not profile.primary_content
        if profile.local_language:
            assert set(cap.support.languages) - {"en"}
            assert cap.family != "news_discovery"
    assert not profiles["research_regional_cdt_zh"].local_language
    assert profiles[PARLIAMENT].primary_content
    assert not profiles["research_publisher_gov_uk_mod_news"].primary_content
    with pytest.raises(TypeError):
        result.reviewed_profiles["unknown"] = profiles[PARLIAMENT]


@pytest.mark.parametrize("index", range(3), ids=["ukraine-drone", "cyber", "economy"])
def test_production_profiles_preserve_curated_source_choices(index):
    audit = json.loads(
        (Path(__file__).parent / "fixtures/source_allocator_e01.json").read_text("utf8")
    )
    query, requirements, _, options = scenario(audit, index)
    case = audit["cases"][index]
    ids = tuple(case["source_ids"])
    context = compose_research_allocation(ids, enabled=dict.fromkeys(ids, True))
    options.update(
        authorised_ids=context.authorised_ids, reviewed_profiles=context.reviewed_profiles
    )
    result = allocate_sources(query, requirements, context.resolved, **options)
    assert result.provider_ids[0] == case["expected_first"]
    assert set(case["must_plan"]) <= set(result.provider_ids)
    assert not set(case["must_exclude"]) & set(result.provider_ids)
    assert (
        compose_research_allocation(tuple(reversed(ids)), enabled=dict.fromkeys(ids, True))
        == context
    )


@pytest.mark.parametrize("focus", list(ResearchFocus))
def test_real_factory_ids_are_supported_without_constructing_new_routes(focus):
    service = research_service(Mock(), Mock())
    query = ResearchQuery(
        "Review company and domain infrastructure",
        NOW - timedelta(days=1),
        NOW,
        focus=focus,
        subject="example.com",
        mode=ResearchMode.ADVANCED,
    )
    ids = tuple(provider.id for provider in service._providers(query))
    context = compose_research_allocation(ids, enabled=dict.fromkeys(ids, True))
    assert {row.capability.id for row in context.resolved} == set(ids)
    if focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}:
        assert not context.authorised_ids


def test_real_area_factory_requires_explicit_retained_store_presence():
    service = research_service(Mock(), Mock(), retained_store=Mock())
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                    },
                }
            ],
        }
    )
    query = ResearchQuery(
        "Review earthquakes in this area", NOW - timedelta(days=1), NOW, area=area
    )
    ids = tuple(provider.id for provider in service._providers(query))
    retained = "research-retained-area-feeds"
    assert retained in ids
    context = compose_research_allocation(ids, enabled=dict.fromkeys(ids, True))
    assert retained not in context.authorised_ids
    context = compose_research_allocation(
        ids, enabled=dict.fromkeys(ids, True), requirements={retained: requirement("runtime", True)}
    )
    assert retained in context.authorised_ids


@pytest.mark.parametrize(
    "present,kind,readiness",
    [
        (None, "api_key", CapabilityReadiness.REQUIREMENT_UNKNOWN),
        (False, "api_key", CapabilityReadiness.REQUIREMENT_MISSING),
        (True, "api_key", CapabilityReadiness.CONFIGURED_UNVERIFIED),
        (True, "runtime", CapabilityReadiness.REQUIREMENT_UNKNOWN),
    ],
)
def test_required_configuration_is_presence_only_and_never_guessed(present, kind, readiness):
    result = compose_research_allocation(
        (CERT,), enabled={CERT: True}, requirements={CERT: requirement(kind, present)}
    )
    assert result.resolved[0].readiness is readiness
    assert bool(result.authorised_ids) == (readiness is CapabilityReadiness.CONFIGURED_UNVERIFIED)


def test_optional_key_absence_does_not_disable_public_scholarly_metadata():
    source = "research-openalex"
    result = compose_research_allocation(
        (source,),
        enabled={source: True},
        requirements={source: requirement("api_key", False, optional=True)},
    )
    assert result.authorised_ids == {source}
    assert result.resolved[0].readiness is CapabilityReadiness.PUBLIC_UNVERIFIED


@pytest.mark.parametrize(
    "enabled,disabled",
    [
        ({}, frozenset()),
        ({NEWS: False}, frozenset()),
        ({NEWS: 1}, frozenset()),
        ({NEWS: True, "google_news": False}, frozenset()),
        ({NEWS: True, "google_news_watchlists": False}, frozenset()),
        ({NEWS: True}, frozenset({"google_news"})),
        ({NEWS: True}, frozenset({"google_news_watchlists"})),
    ],
)
def test_parent_missing_false_and_nonboolean_admission_fail_closed(enabled, disabled):
    result = compose_research_allocation((NEWS,), enabled=enabled, disabled=disabled)
    assert not result.authorised_ids
    assert result.resolved[0].readiness is CapabilityReadiness.DISABLED


@pytest.mark.parametrize(
    "ids",
    [
        ("unknown",),
        ("gap.cti_kev",),
        ("cisa_kev",),
        ("research_import",),
        ("research-web-search",),
        (NEWS, NEWS),
        [NEWS],
        (None,),
        tuple(f"id-{i}" for i in range(129)),
    ],
)
def test_unknown_nonprovider_duplicate_and_unbounded_ids_fail_closed(ids):
    with pytest.raises(ValueError, match="registered research provider IDs"):
        compose_research_allocation(ids, enabled={})


def test_unreviewed_registry_change_cannot_silently_enter_allocation(monkeypatch):
    profiles = dict(research_allocation_profiles())
    profiles.pop(NEWS)
    monkeypatch.setattr(composition, "research_allocation_profiles", lambda: profiles)
    with pytest.raises(ValueError, match="without reviewed allocation profiles"):
        compose_research_allocation((NEWS,), enabled={NEWS: True})


@pytest.mark.parametrize(
    "value", [object(), replace(requirement("api_key", True), satisfied="yes")]
)
def test_requirement_input_rejects_untyped_or_truthy_values(value):
    with pytest.raises(ValueError, match="safe typed presence"):
        compose_research_allocation((CERT,), enabled={CERT: True}, requirements={CERT: value})


def test_presence_values_and_unrelated_inventory_details_never_enter_context():
    needs = {CERT: replace(requirement("api_key", True), note="SENSITIVE", setting="PRIVATE_PATH")}
    context = compose_research_allocation(
        (CERT,), enabled={CERT: True, "dashboard_only": True}, requirements=needs
    )
    needs.clear()
    assert context.authorised_ids == {CERT}
    assert "SENSITIVE" not in repr(context) and "PRIVATE_PATH" not in repr(context)
    assert "dashboard_only" not in repr(context)


@pytest.mark.asyncio
async def test_loader_reads_current_parent_controls_once_and_never_takes_a_guard():
    admission = Mock()
    admission.enabled_many = AsyncMock(return_value={NEWS: True, "google_news_watchlists": False})
    result = await load_research_allocation((NEWS,), admission=admission)
    admission.enabled_many.assert_awaited_once_with(("google_news", "google_news_watchlists", NEWS))
    admission.guard.assert_not_called()
    assert not result.authorised_ids


@pytest.mark.asyncio
async def test_empty_or_invalid_provider_inventory_makes_no_admission_call():
    admission = Mock(enabled_many=AsyncMock())
    assert not (await load_research_allocation((), admission=admission)).resolved
    with pytest.raises(ValueError):
        await load_research_allocation(("unknown",), admission=admission)
    admission.enabled_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_admission_failure_propagates_without_optimistic_context():
    admission = Mock(enabled_many=AsyncMock(side_effect=RuntimeError("Unavailable")))
    with pytest.raises(RuntimeError, match="Unavailable"):
        await load_research_allocation((NEWS,), admission=admission)
