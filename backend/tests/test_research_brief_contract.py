"""Canonical Research Brief definitions stay bounded, versioned and lossless."""

import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ase.application.reports.request import ReportRequest
from ase.application.research.brief_codec import brief_from_dict, brief_to_dict
from ase.application.research.brief_conversion import (
    brief_from_legacy_request,
    legacy_request_from_brief,
)
from ase.application.research.brief_limits import BriefAuthorisedCaps, resolve_brief_limits
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.map_research_origin import MapResearchOrigin
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import ResearchArea
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_scope import (
    BriefCollection,
    BriefObservation,
    BriefPrivateInput,
    BriefScope,
)
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefIndicator,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
    IntelligenceRequirement,
    LensId,
)
from ase.domain.research_plan import QueryVariant
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate

BRIEF_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
TEAM_ID = UUID("33333333-3333-4333-8333-333333333333")
REPORT_ID = UUID("44444444-4444-4444-8444-444444444444")
INPUT_ID = UUID("55555555-5555-4555-8555-555555555555")
WHEN = datetime(2026, 9, 1, tzinfo=UTC)


def brief(**changes: object) -> ResearchBrief:
    parts = {
        "identity": BriefIdentity(BRIEF_ID, 1, OWNER_ID, "Energy brief", WHEN, WHEN),
        "question": BriefQuestion("What changed in energy supply?"),
        "scope": BriefScope(country_isos=("GB",)),
        "observation": BriefObservation("relative", lookback_hours=168),
        "lens": BriefLens(),
        "collection": BriefCollection(),
        "output": BriefOutput(ResearchMode.QUICK),
        "limits": BriefLimits(),
        "monitoring": BriefMonitoring(),
    }
    parts.update(changes)
    return ResearchBrief(**parts)


def test_maximal_advanced_brief_round_trips_all_requirement_ids_and_choices() -> None:
    requirements = tuple(
        IntelligenceRequirement(
            f"req-{index}", f"Assess question {index}: exact source text", index <= 12, index
        )
        for index in range(1, 13)
    )
    original = brief(
        identity=BriefIdentity(
            BRIEF_ID,
            4,
            OWNER_ID,
            "Advanced energy brief",
            WHEN,
            WHEN + timedelta(days=1),
            team_id=TEAM_ID,
            preset_id="energy-uk",
            preset_version=2,
            published=True,
        ),
        question=BriefQuestion("What changed in energy supply?", requirements, ("Ignore rumours",)),
        scope=BriefScope(country_isos=("GB",), parent_report_id=REPORT_ID, parent_version=3),
        observation=BriefObservation(
            "explicit",
            since=WHEN - timedelta(days=30),
            until=WHEN,
            time_basis=EvidenceTimeBasis.PUBLICATION,
            forecast_horizon_days=30,
        ),
        lens=BriefLens(LensId.UK_POLICY, "UK analyst", "Plan for disruption", "Rank relevance"),
        collection=BriefCollection(
            languages=("en", "fr"),
            terms=("energy",),
            query_variants=(QueryVariant("fr", ("énergie",), original_terms=("energy",)),),
            source_policy="selected_only",
            source_ids=("gdelt_news",),
            web_search=True,
            candidate_hypotheses=(ResearchCandidate("c-1", "Supply disruption"),),
            planned_tasks=(PlannedQueryTask("t-1", "gdelt_news", "challenge", ("supply",)),),
            require_primary=True,
            require_local=True,
            require_opposition=True,
        ),
        output=BriefOutput(
            ResearchMode.ADVANCED,
            language="fr",
            preferred_sections=("timeline", "requirements"),
            chart_preference="prefer",
            table_preference="prefer",
        ),
        limits=BriefLimits(
            max_passes=2,
            max_external_operations=32,
            max_model_calls=24,
            max_output_tokens=256_000,
            max_collection_seconds=240,
        ),
        monitoring=BriefMonitoring(
            indicators=(BriefIndicator("supply", "Official supply warning"),),
            review_conditions=("Source disagreement changes",),
            prefer_novelty=True,
        ),
        private_inputs=(
            BriefPrivateInput("durable_report", report_id=REPORT_ID, report_version=3),
        ),
    )
    stored = brief_to_dict(original)
    restored = brief_from_dict(json.loads(json.dumps(stored)))
    assert restored == original
    assert [row.id for row in restored.question.requirements] == [f"req-{i}" for i in range(1, 13)]
    assert [row.question for row in restored.question.requirements] == [
        f"Assess question {i}: exact source text" for i in range(1, 13)
    ]
    assert stored["identity"]["schema_version"] == 1
    assert brief_to_dict(restored) == stored


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda: BriefQuestion("x" * 2001), "question.main"),
        (
            lambda: BriefQuestion(
                "Question", tuple(IntelligenceRequirement(str(i), "Q") for i in range(13))
            ),
            "question.requirements",
        ),
        (lambda: BriefLens(audience="x" * 1001), "lens.audience"),
        (lambda: BriefLimits(max_model_calls=25), "limits.max_model_calls"),
    ],
)
def test_rejects_overlong_or_over_cap_fields(factory: Callable[[], object], field: str) -> None:
    with pytest.raises(BriefValidationError) as caught:
        factory()
    assert caught.value.field == field


def test_required_tier_count_and_duplicate_ids_are_never_silently_trimmed() -> None:
    requirements = tuple(IntelligenceRequirement(f"r-{i}", f"Question {i}") for i in range(4))
    with pytest.raises(BriefValidationError, match="deeper") as caught:
        brief(question=BriefQuestion("Main", requirements))
    assert caught.value.field == "question.requirements"
    with pytest.raises(BriefValidationError, match="unique"):
        BriefQuestion("Main", (requirements[0], requirements[0]))


def test_revision_keeps_published_source_immutable_and_rejects_unknown_saved_fields() -> None:
    source = brief(identity=replace(brief().identity, published=True))
    revised = source.revise(at=WHEN + timedelta(seconds=1), question=BriefQuestion("New question"))
    assert source.identity.revision == 1 and source.identity.published
    assert revised.identity.revision == 2 and not revised.identity.published
    assert source.question.main == "What changed in energy supply?"
    with pytest.raises(FrozenInstanceError):
        source.question.main = "Changed"  # type: ignore[misc]
    stored = brief_to_dict(source)
    stored["identity"]["unknown"] = "drop me"
    with pytest.raises(BriefValidationError, match="canonical"):
        brief_from_dict(stored)


def test_recorded_history_needs_exact_dates_and_rolling_time_resolves_once() -> None:
    historical = brief(
        observation=BriefObservation(
            "explicit",
            since=WHEN - timedelta(days=2000),
            until=WHEN,
            time_basis=EvidenceTimeBasis.RECORDED,
        )
    )
    assert historical.observation.resolved_interval(WHEN) == (WHEN - timedelta(days=2000), WHEN)
    with pytest.raises(BriefValidationError, match="rolling"):
        BriefObservation("relative", lookback_hours=24, time_basis=EvidenceTimeBasis.RECORDED)
    rolling = brief().observation
    assert rolling.resolved_interval(WHEN) == (WHEN - timedelta(hours=168), WHEN)


def test_drawn_and_saved_map_areas_keep_exact_geometry_and_origin_hashes() -> None:
    geometry = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[10, 40], [12, 40], [12, 42], [10, 42], [10, 40]]],
                },
            }
        ],
    }
    area = ResearchArea(parse_map_geometry(json.dumps(geometry)))
    drawn = brief(scope=BriefScope(area=area))
    assert drawn.scope.geometry_version == 1
    assert drawn.scope.area_hash == area.geometry.sha256
    assert brief_from_dict(brief_to_dict(drawn)) == drawn
    origin = MapResearchOrigin(BRIEF_ID, INPUT_ID, REPORT_ID, TEAM_ID, 2, "a" * 64, "b" * 64, area)
    saved = brief(scope=BriefScope(map_origin=origin))
    assert saved.scope.area_hash == drawn.scope.area_hash
    assert brief_from_dict(brief_to_dict(saved)).scope.map_origin == origin


def test_session_inputs_cannot_become_subscriptions_or_public_queries() -> None:
    private = brief(
        scope=BriefScope(focus=ResearchFocus.DOCUMENT),
        private_inputs=(BriefPrivateInput("session", input_id=INPUT_ID, expires_at=WHEN),),
    )
    with pytest.raises(BriefValidationError, match="Renew"):
        private.require_subscription_ready(now=WHEN)
    with pytest.raises(BriefValidationError, match="expired"):
        private.require_live_inputs(now=WHEN)
    with pytest.raises(BriefValidationError, match="public collection"):
        replace(private, collection=BriefCollection(web_search=True))


def test_legacy_request_preserves_existing_choices_without_inventing_new_preferences() -> None:
    old = ReportRequest(
        template_id="ask",
        question="What changed in energy supply?",
        research_mode=ResearchMode.DETAILED,
        country_isos=("GB",),
        team_id=TEAM_ID,
        window_hours=168,
        research_languages=("en", "fr"),
        research_terms=("energy",),
        research_source_ids=("gdelt_news",),
        research_web_search=True,
        report_language="fr",
        devils_advocacy=True,
    )
    converted = brief_from_legacy_request(
        old, brief_id=BRIEF_ID, owner_id=OWNER_ID, title="Energy brief", created_at=WHEN
    )
    assert converted.identity.origin == "legacy-derived"
    assert converted.question.requirements == ()
    assert converted.monitoring.prefer_novelty is None
    assert converted.limits.max_model_calls is None
    assert brief_from_dict(brief_to_dict(converted)) == converted
    assert legacy_request_from_brief(converted) == old


def test_legacy_parent_without_an_exact_version_requires_resolution() -> None:
    old = ReportRequest(
        template_id="ask",
        question="What changed?",
        research_mode=ResearchMode.QUICK,
        parent_report_id=REPORT_ID,
    )
    with pytest.raises(BriefValidationError) as caught:
        brief_from_legacy_request(
            old, brief_id=BRIEF_ID, owner_id=OWNER_ID, title="Follow-up", created_at=WHEN
        )
    assert caught.value.field == "scope.parent_version"


def test_legacy_bridge_rejects_new_requirements_instead_of_losing_them() -> None:
    authored = brief(question=BriefQuestion("Main", (IntelligenceRequirement("req-1", "One"),)))
    with pytest.raises(BriefValidationError, match="canonical admission"):
        legacy_request_from_brief(authored)


def test_limits_resolve_against_depth_and_authorised_model_without_mutating_brief() -> None:
    source = brief()
    caps = BriefAuthorisedCaps(2, 32, 12, 40_000, 240)
    effective = resolve_brief_limits(source, caps)
    assert effective.max_external_operations == 6
    assert effective.max_collection_seconds == 45
    assert effective.max_model_calls == 12
    assert effective.max_output_tokens == 40_000
    assert source.limits.max_model_calls is None
    with pytest.raises(BriefValidationError) as caught:
        resolve_brief_limits(replace(source, limits=BriefLimits(max_external_operations=7)), caps)
    assert caught.value.field == "limits.max_external_operations"
