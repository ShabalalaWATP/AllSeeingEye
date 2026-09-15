"""Pure exact-brief preflight: no collection, model work, scope widening or hidden reductions."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.access import AccessContext
from ase.application.research.preflight import preview_brief
from ase.application.source_capabilities import CapabilityReadiness
from ase.application.source_inventory import SourceRequirement
from ase.container.research_capabilities import research_capability_registry
from ase.domain.errors import NotFound
from ase.domain.events import Category
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import direct_area_from_geometry
from ase.domain.research_brief_scope import (
    BriefCollection,
    BriefObservation,
    BriefPrivateInput,
    BriefScope,
)
from ase.domain.research_brief_values import (
    BriefLimits,
    BriefQuestion,
    BriefValidationError,
    IntelligenceRequirement,
)
from ase.domain.users import Role, User
from test_research_brief_persistence import NOW, _brief


def _access(owner_id):
    actor = User(
        owner_id, "preview@example.com", "Preview", Role.USER, True, None, 0, None, None, NOW, None
    )
    return AccessContext(actor, {}, {})


def _preview(brief, **kwargs):
    return preview_brief(
        brief,
        _access(brief.identity.owner_id),
        now=NOW,
        registry=research_capability_registry(),
        **kwargs,
    )


@pytest.mark.parametrize(
    ("mode", "operations", "seconds", "questions"),
    [
        (ResearchMode.QUICK, 6, 45, 3),
        (ResearchMode.DETAILED, 24, 180, 6),
        (ResearchMode.ADVANCED, 32, 240, 12),
    ],
)
def test_tier_ceilings_and_every_requirement_are_preserved(mode, operations, seconds, questions):
    brief = _brief()
    requirements = tuple(
        IntelligenceRequirement(f"q{i}", f"Question {i}?") for i in range(questions)
    )
    brief = replace(
        brief,
        output=replace(brief.output, depth=mode),
        question=BriefQuestion("Central question?", requirements),
    )
    result = _preview(brief)
    assert result.requirements == requirements
    assert result.budget.source_operation_ceiling == operations
    assert result.budget.collection_second_ceiling == seconds
    assert result.budget.required_question_ceiling == questions
    assert result.budget.model_call_ceiling == 24
    assert result.budget.output_token_ceiling == 256000
    assert not result.admission_checked and not result.budget.reservations_made
    assert result.model_calls == result.provider_calls == 0
    assert result.model_compatibility == "not_checked"
    assert "generation time varies" in result.duration_note


def test_relative_explicit_and_template_default_dates_do_not_mutate_definition():
    brief = _brief()
    default = _preview(brief)
    assert default.since == NOW - timedelta(hours=72)
    assert default.until == NOW
    assert default.requirements[0].question == brief.question.main
    relative = replace(
        brief,
        observation=BriefObservation("relative", lookback_hours=120, forecast_horizon_days=30),
    )
    result = _preview(relative)
    assert result.since == NOW - timedelta(hours=120)
    assert result.until == NOW and result.forecast_horizon_days == 30
    assert relative.observation.since is None
    explicit = replace(
        brief,
        observation=BriefObservation(
            "explicit", since=NOW - timedelta(days=12), until=NOW - timedelta(days=9)
        ),
    )
    result = _preview(explicit)
    assert (result.since, result.until) == (explicit.observation.since, explicit.observation.until)
    assert result.time_basis is EvidenceTimeBasis.PUBLICATION


def test_requested_limits_are_visible_and_too_large_is_explicit_review():
    brief = replace(
        _brief(),
        limits=BriefLimits(
            max_external_operations=3,
            max_collection_seconds=20,
            max_model_calls=5,
            max_output_tokens=12000,
        ),
    )
    result = _preview(brief)
    assert result.budget.requested == brief.limits
    assert result.budget.source_operation_ceiling == 3
    assert result.budget.collection_second_ceiling == 20
    assert result.budget.model_call_ceiling == 5
    larger = replace(brief, limits=BriefLimits(max_external_operations=24))
    result = _preview(larger)
    assert "max_external_operations_exceeds_tier_ceiling" in result.review_reasons
    assert result.budget.requested.max_external_operations == 24
    assert result.budget.source_operation_ceiling == 6


def test_selected_sources_language_readiness_and_gaps_remain_distinct():
    ids = (
        "research_publisher_cyber_ncsc_news",
        "research_publisher_cyber_cert_fr",
        "research-certificate-transparency",
        "gap.cti_kev",
        "unknown-source",
    )
    brief = replace(
        _brief(),
        scope=BriefScope(categories=(Category.CYBER,)),
        collection=BriefCollection(source_policy="selected_only", source_ids=ids),
    )
    result = _preview(brief, enabled={key: key != ids[0] for key in ids})
    rows = {row.capability.id: row for row in result.sources}
    assert rows[ids[0]].readiness is CapabilityReadiness.DISABLED
    assert "language_not_supported" in rows[ids[1]].exclusion_reasons
    assert rows[ids[2]].readiness is CapabilityReadiness.REQUIREMENT_UNKNOWN
    assert result.unknown_source_ids == ids[3:]
    assert not result.candidate_provider_ids
    assert "unknown_source_ids" in result.review_reasons
    assert "gap.cti_kev" in {row.id for row in result.gaps}
    assert set(rows) <= set(ids)


def test_configured_domain_route_is_only_unverified_current_context():
    source_id = "research-certificate-transparency"
    brief = replace(
        _brief(),
        scope=BriefScope(focus=ResearchFocus.DOMAIN, subject="example.com"),
        collection=BriefCollection(source_policy="selected_only", source_ids=(source_id,)),
    )
    result = _preview(
        brief,
        requirements={
            source_id: SourceRequirement("api_key", True, "environment", None, "Presence only")
        },
    )
    assert result.candidate_provider_ids == (source_id,)
    assert result.sources[0].readiness is CapabilityReadiness.CONFIGURED_UNVERIFIED
    assert "Current snapshot" in result.sources[0].date_note


def test_recorded_interval_excludes_publication_only_routes():
    brief = replace(
        _brief(),
        observation=BriefObservation(
            "explicit",
            since=NOW - timedelta(days=12),
            until=NOW,
            time_basis=EvidenceTimeBasis.RECORDED,
        ),
        collection=BriefCollection(
            source_policy="selected_only", source_ids=("research_publisher_bbc_world",)
        ),
    )
    result = _preview(brief)
    assert result.sources[0].exclusion_reasons == ("recorded_interval_not_supported",)
    assert not result.candidate_provider_ids


def test_saved_map_and_private_input_checks_are_never_assumed():
    brief = replace(_brief(), scope=BriefScope(map_view_id=uuid4(), map_revision_id=uuid4()))
    result = _preview(brief)
    assert result.scope.saved_map_resolution_required
    assert result.scope.area_sha256 is None
    assert not result.candidate_provider_ids
    private = replace(
        _brief(),
        scope=BriefScope(focus=ResearchFocus.DOCUMENT),
        private_inputs=(
            BriefPrivateInput(
                kind="session", input_id=uuid4(), expires_at=NOW - timedelta(seconds=1)
            ),
        ),
    )
    result = _preview(private)
    assert result.scope.linked_context_checks_required
    assert "private_input_expired" in result.review_reasons
    assert not result.candidate_provider_ids
    assert all("private_input_scope" in row.exclusion_reasons for row in result.sources)


def test_drawn_area_requires_disclosure_for_fresh_sources_but_preserves_its_hash():
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-1, 51], [0, 51], [0, 52], [-1, 52], [-1, 51]]],
                    },
                }
            ],
        }
    )
    assert area is not None
    brief = replace(
        _brief(),
        scope=BriefScope(area=area),
        collection=BriefCollection(
            source_policy="selected_only", source_ids=("research-usgs-area",)
        ),
    )
    result = _preview(brief)
    assert result.scope.area_sha256 == area.geometry.sha256
    assert result.time_basis is EvidenceTimeBasis.RESEARCH
    assert "area_disclosure_required" in result.sources[0].exclusion_reasons
    allowed = replace(brief, scope=replace(brief.scope, disclose_area_to_provider=True))
    assert _preview(allowed).candidate_provider_ids == ("research-usgs-area",)
    assert "gap.area_history" in {gap.id for gap in result.gaps}


def test_empty_selection_unknown_template_and_foreign_scope_fail_honestly():
    brief = replace(
        _brief(), collection=BriefCollection(source_policy="selected_only", source_ids=())
    )
    assert not _preview(brief).sources
    invalid = replace(brief, output=replace(brief.output, template_id="not-real"))
    with pytest.raises(BriefValidationError, match="supported template"):
        _preview(invalid)
    with pytest.raises(NotFound):
        preview_brief(brief, _access(uuid4()), now=NOW, registry=research_capability_registry())
    with pytest.raises(ValueError, match="timezone-aware"):
        preview_brief(
            brief,
            _access(brief.identity.owner_id),
            now=NOW.replace(tzinfo=None),
            registry=research_capability_registry(),
        )


def test_copies_are_one_origin_and_web_has_an_explicit_unchecked_allowance():
    brief = replace(
        _brief(),
        collection=BriefCollection(
            source_policy="selected_only",
            web_search=True,
            source_ids=("research_publisher_bbc_world", "research_publisher_economic_bbc_business"),
        ),
    )
    result = _preview(brief)
    assert len(result.candidate_provider_ids) == 2
    assert result.known_origin_group_count == 1
    assert result.unknown_origin_capability_count == 0
    assert "fresh_web_model_and_separate_allowance_not_checked" in result.review_reasons
