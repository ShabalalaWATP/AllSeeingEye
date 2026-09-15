"""Curated E01 allocation behaviour, truthful limits and immutable public-query boundaries."""

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from ase.adapters.research_subjects.parliament import ParliamentQuestionsProvider
from ase.adapters.research_subjects.world_bank import WorldBankProvider
from ase.application.research.source_allocation_types import POLICY_VERSION, AllocationProfile
from ase.application.research.source_allocator import allocate_sources
from ase.application.source_capabilities import CapabilityReadiness, ResolvedCapability
from ase.container.research_capabilities import research_capability_registry
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.source_capabilities import (
    CapabilityScope,
    ContentCapability,
    DateSupport,
    ExecutionRoute,
)

NOW = datetime(2026, 9, 14, tzinfo=UTC)


@pytest.fixture
def audit():
    return json.loads(
        (Path(__file__).parent / "fixtures/source_allocator_e01.json").read_text("utf8")
    )


def scenario(audit, index=0):
    case = audit["cases"][index]
    registry = research_capability_registry()
    query = ResearchQuery(
        case["question"],
        NOW - timedelta(days=7),
        NOW,
        languages=tuple(case["languages"]),
        terms=tuple(case["terms"]),
        mode=ResearchMode.DETAILED,
        country_isos=tuple(case["countries"]),
        subject=case["subject"],
    )
    requirements = tuple(
        IntelligenceRequirement(f"q{i}", question, priority=i)
        for i, question in enumerate(case["requirements"], 1)
    )
    resolved = tuple(
        ResolvedCapability(registry.capabilities[key], CapabilityReadiness.PUBLIC_UNVERIFIED)
        for key in case["source_ids"]
    )
    profiles = {
        key: AllocationProfile(
            tuple(audit["profiles"][key]["terms"]),
            audit["review_note"],
            tuple(audit["profiles"][key]["countries"]),
            audit["profiles"][key]["primary_content"],
            audit["profiles"][key]["local_language"],
        )
        for key in case["source_ids"]
    }
    options = {
        "authorised_ids": frozenset(case["source_ids"]),
        "provider_support": dict.fromkeys(case["source_ids"], True),
        "reviewed_profiles": profiles,
        "accepted_dates": tuple(DateSupport(value) for value in case["accepted_dates"]),
    }
    return query, requirements, resolved, options


@pytest.mark.parametrize("index", range(3), ids=["ukraine-drone", "cyber", "economy"])
def test_curated_relevant_sources_beat_unrelated_families(audit, index):
    query, requirements, resolved, options = scenario(audit, index)
    before = asdict(query)
    result = allocate_sources(query, requirements, resolved, **options)
    case = audit["cases"][index]
    assert result.policy_version == audit["policy_version"] == POLICY_VERSION
    assert result.provider_ids[0] == case["expected_first"]
    assert set(case["must_plan"]) <= set(result.provider_ids)
    assert not set(case["must_exclude"]) & set(result.provider_ids)
    assert asdict(query) == before
    assert result == allocate_sources(
        query, tuple(reversed(requirements)), tuple(reversed(resolved)), **options
    )
    for key in case["must_exclude"]:
        receipt = next(row for row in result.receipts if row.source_id == key)
        assert receipt.disposition == "excluded" and "no_reviewed_relevance" in receipt.reasons
    assert result.attempted_operations == result.transport_requests == result.returned_items == 0
    assert result.retained_items == result.selected_items == 0 and result.retrieved_at is None
    assert result.planned_operations == len(result.provider_ids)
    assert result.catalogue_capabilities == len(resolved)
    assert result.max_public_concurrency == 2 and result.max_per_host_concurrency == 1
    if index in (0, 2):
        provider_type = ParliamentQuestionsProvider if index == 0 else WorldBankProvider
        assert provider_type(Mock(), Mock()).supports(query)
    assert all(row.declared_dates for row in result.receipts)


def test_operator_terms_retain_relevant_sources_when_question_is_generic(audit):
    query, _, resolved, options = scenario(audit)
    query = replace(query, question="What happened?", subject=None, terms=("Ukraine drones",))
    result = allocate_sources(query, (), resolved, **options)
    assert result.provider_ids
    assert any(
        ("operator_terms", 8) in row.score_components
        for row in result.receipts
        if row.disposition == "planned"
    )
    assert "Ukraine drones" not in repr(result)


def test_exact_provider_support_dominates_relevance_and_brand_is_not_primary(audit):
    query, requirements, resolved, options = scenario(audit)
    parliament = "research-uk-parliament"
    query = replace(query, country_isos=("UA",), country_iso=None)
    options["provider_support"][parliament] = False
    # Even a mistaken primary label cannot turn MOD RSS into primary passages.
    mod = "research_publisher_gov_uk_mod_news"
    options["reviewed_profiles"][mod] = replace(
        options["reviewed_profiles"][mod], primary_content=True
    )
    result = allocate_sources(query, requirements, resolved, **options)
    assert parliament not in result.provider_ids and mod in result.provider_ids
    assert result.reservations[0].planned == 0
    assert result.reservations[0].reason == "no_relevant_capability"
    receipt = next(row for row in result.receipts if row.source_id == parliament)
    assert "exact_provider_support_missing" in receipt.reasons


@pytest.mark.parametrize(
    "mode,expected",
    [
        (ResearchMode.QUICK, (6, 0, 45, 0, 200, 0)),
        (ResearchMode.DETAILED, (20, 4, 135, 45, 792, 8)),
        (ResearchMode.ADVANCED, (26, 6, 180, 60, 988, 12)),
    ],
)
def test_phase_allowances_keep_challenge_time_operations_and_items_reserved(audit, mode, expected):
    query, requirements, resolved, options = scenario(audit)
    result = allocate_sources(replace(query, mode=mode), requirements, resolved, **options)
    assert tuple(asdict(result.phases).values()) == expected
    assert result.planned_operations <= result.phases.initial_operations
    assert result.reservations[0].requested == {"quick": 1, "detailed": 2, "advanced": 3}[mode]
    assert result.reservations[1].reason == "not_requested"


def test_all_exclusion_paths_are_visible_and_private_terms_never_enter_receipts(audit):
    query, requirements, resolved, options = scenario(audit)
    chosen = resolved[0].capability.id
    options["authorised_ids"] = frozenset()
    options["provider_support"] = {}
    options["reviewed_profiles"] = {}
    unsupported = tuple(replace(row, readiness=CapabilityReadiness.DISABLED) for row in resolved)
    query = replace(
        query,
        focus=ResearchFocus.DOCUMENT,
        country_iso=None,
        country_isos=(),
        source_ids=(chosen,),
        question="PRIVATE_SENTINEL with Ukraine drones",
        terms=("approved public term",),
    )
    result = allocate_sources(query, requirements, unsupported, **options)
    assert not result.provider_ids
    reasons = {reason for row in result.receipts for reason in row.reasons}
    assert {
        "private_scope",
        "source_policy",
        "not_authorised",
        "disabled",
        "exact_provider_support_missing",
        "unreviewed_profile",
    } <= reasons
    assert "PRIVATE_SENTINEL" not in repr(result)
    assert "approved public term" not in repr(result)
    assert query.terms == ("approved public term",)


def test_language_date_scope_and_non_provider_routes_fail_closed(audit):
    query, requirements, resolved, options = scenario(audit)
    first = resolved[0]
    cap = replace(
        first.capability,
        route=ExecutionRoute.PRIVATE_DOCUMENT,
        support=replace(
            first.capability.support,
            languages=("zh",),
            dates=(DateSupport.CURRENT_SNAPSHOT,),
            scopes=(CapabilityScope.DOMAIN,),
        ),
    )
    rows = (replace(first, capability=cap), *resolved[1:])
    result = allocate_sources(query, requirements, rows, **options)
    receipt = next(row for row in result.receipts if row.source_id == cap.id)
    assert {
        "non_provider_route",
        "unsupported_language",
        "unsupported_dates",
        "unsupported_scope",
    } <= set(receipt.reasons)


def test_local_language_reservation_and_short_budget_receipts(audit):
    query, requirements, resolved, options = scenario(audit, 1)
    result = allocate_sources(query, requirements, resolved, **options)
    assert result.reservations[1].requested == result.reservations[1].planned == 1
    assert result.reservations[1].reason == "satisfied"
    stopped = allocate_sources(query, requirements, resolved, max_operations=4, **options)
    assert not stopped.provider_ids and stopped.phases.challenge_operations == 4
    assert any(row.disposition == "not_planned_capacity" for row in stopped.receipts)
    assert stopped.reservations[1].reason == "initial_operation_cap"
    assert all(not ids for _, ids in stopped.requirement_sources)


def test_same_origin_variants_do_not_inflate_diversity_or_win_ties(audit):
    query, _requirements, resolved, options = scenario(audit, 1)
    keys = tuple(options["reviewed_profiles"])
    profile = AllocationProfile(("exploitation",), "Synthetic origin-diversity fixture")
    options["reviewed_profiles"] = dict.fromkeys(keys, profile)
    common = resolved[0].capability
    rows = tuple(
        replace(
            row,
            capability=replace(
                common,
                id=row.capability.id,
                origin_group="same" if index < 2 else "other" if index == 2 else None,
            ),
        )
        for index, row in enumerate(resolved)
    )
    result = allocate_sources(
        replace(query, mode=ResearchMode.QUICK), (), rows, max_operations=3, **options
    )
    by_id = {row.capability.id: row.capability.origin_group for row in rows}
    assert len({by_id[key] for key in result.provider_ids}) == 3
    assert result.known_origin_groups == 2 and result.unknown_origin_operations == 1
    assert result == allocate_sources(
        replace(query, mode=ResearchMode.QUICK),
        (),
        tuple(reversed(rows)),
        max_operations=3,
        **options,
    )


@pytest.mark.parametrize("invalid", [-1, True, 25])
def test_operation_cap_rejects_invalid_or_excessive_values(audit, invalid):
    query, requirements, resolved, options = scenario(audit)
    with pytest.raises(ValueError, match="Operation limit"):
        allocate_sources(query, requirements, resolved, max_operations=invalid, **options)


def test_unknown_source_ids_profiles_and_missing_metadata_are_not_admitted(audit):
    query, requirements, resolved, options = scenario(audit)
    with pytest.raises(ValueError):
        allocate_sources(
            replace(query, source_ids=("invented",)), requirements, resolved, **options
        )
    with pytest.raises(ValueError):
        allocate_sources(query, requirements, (*resolved, resolved[0]), **options)
    with pytest.raises(ValueError):
        allocate_sources(query, requirements * 2, resolved, **options)
    with pytest.raises(ValueError):
        allocate_sources(query, requirements, resolved, **{**options, "accepted_dates": ()})
    with pytest.raises(ValueError):
        allocate_sources(
            query,
            requirements,
            resolved,
            **{
                **options,
                "reviewed_profiles": {
                    "invented": next(iter(options["reviewed_profiles"].values()))
                },
            },
        )
    for changes in (
        {"terms": ("x" * 81,)},
        {"countries": ("ZZZ",)},
        {"review_note": ""},
        {"primary_content": 1},
    ):
        with pytest.raises(ValueError):
            AllocationProfile(**{"terms": ("drone",), "review_note": "reviewed", **changes})


@pytest.mark.parametrize("mode", list(ResearchMode))
def test_full_initial_plan_respects_overlapping_reservations_and_all_cumulative_caps(audit, mode):
    query, requirements, resolved, _options = scenario(audit, 1)
    base = resolved[0].capability
    # Synthetic uniform capabilities isolate reservation arithmetic. IDs remain
    # real catalogue IDs, but this test does not assert their production support.
    ids = tuple(research_capability_registry().capabilities)[:40]
    support = replace(base.support, languages=("en", "uk"))
    rows = tuple(
        ResolvedCapability(
            replace(
                base,
                id=key,
                origin_group=f"fixture-{i}",
                content=ContentCapability.STRUCTURED,
                support=support,
            ),
            CapabilityReadiness.PUBLIC_UNVERIFIED,
        )
        for i, key in enumerate(ids)
    )
    profile = AllocationProfile(
        ("exploitation", "vulnerabilities", "campaign", "mitigation"),
        "Synthetic arithmetic fixture",
        primary_content=True,
        local_language=True,
    )
    result = allocate_sources(
        replace(query, mode=mode),
        requirements,
        rows,
        authorised_ids=frozenset(ids),
        provider_support=dict.fromkeys(ids, True),
        reviewed_profiles=dict.fromkeys(ids, profile),
    )
    assert len(result.provider_ids) == {"quick": 6, "detailed": 20, "advanced": 26}[mode]
    assert all(row.planned == row.requested for row in result.reservations)
    assert (
        result.phases.initial_items + result.phases.challenge_items
        == {
            "quick": 200,
            "detailed": 800,
            "advanced": 1000,
        }[mode]
    )
    assert (
        result.planned_operations + result.phases.challenge_operations
        == {
            "quick": 6,
            "detailed": 24,
            "advanced": 32,
        }[mode]
    )
    assert len(set(result.provider_ids)) == len(result.provider_ids)
    assert result.attempted_operations == 0


def test_requirement_priority_and_explicit_source_policy_survive_low_budget(audit):
    query, requirements, resolved, options = scenario(audit)
    mod = "research_publisher_gov_uk_mod_news"
    sources = (mod, "research_regional_ukrinform_en")
    query = replace(query, mode=ResearchMode.QUICK, source_ids=sources)
    requirements = (
        IntelligenceRequirement("civilian", "civilian displacement", priority=1),
        IntelligenceRequirement("drone", "drone warfare", priority=2),
    )
    result = allocate_sources(query, requirements, resolved, max_operations=1, **options)
    assert result.provider_ids == ("research_regional_ukrinform_en",)
    assert dict(result.requirement_sources)["civilian"] == result.provider_ids
    assert query.source_ids == sources
    assert any("source_policy" in row.reasons for row in result.receipts)
