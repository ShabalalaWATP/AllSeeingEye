"""Boundary and losslessness checks for stored Research Brief definitions."""

from collections.abc import Callable
from dataclasses import replace
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
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_brief import MAX_BRIEF_BYTES, ResearchBrief
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
)
from ase.domain.research_plan import QueryVariant

BRIEF_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
REPORT_ID = UUID("44444444-4444-4444-8444-444444444444")
INPUT_ID = UUID("55555555-5555-4555-8555-555555555555")
WHEN = datetime(2026, 9, 1, tzinfo=UTC)


def brief(**changes: object) -> ResearchBrief:
    parts = {
        "identity": BriefIdentity(BRIEF_ID, 1, OWNER_ID, "Brief", WHEN, WHEN),
        "question": BriefQuestion("What changed?"),
        "scope": BriefScope(),
        "observation": BriefObservation("relative", lookback_hours=24),
        "lens": BriefLens(),
        "collection": BriefCollection(),
        "output": BriefOutput(ResearchMode.QUICK),
        "limits": BriefLimits(),
        "monitoring": BriefMonitoring(),
    }
    parts.update(changes)
    return ResearchBrief(**parts)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda: replace(brief().identity, schema_version=2), "schema_version"),
        (lambda: replace(brief().identity, id="bad"), "identity"),
        (lambda: replace(brief().identity, preset_id="preset"), "preset"),
        (lambda: replace(brief().identity, published=1), "published"),
        (lambda: replace(brief().identity, revised_at=WHEN - timedelta(seconds=1)), "revised_at"),
        (lambda: IntelligenceRequirement("bad id", "Question"), "requirements.id"),
        (lambda: IntelligenceRequirement("req", "Q" * 501), "requirements.question"),
        (lambda: IntelligenceRequirement("req", "Question", priority=0), "requirements"),
        (lambda: BriefQuestion("Main", exclusions=("\x00hidden",)), "question.exclusions"),
        (lambda: BriefLens(id="unsupported"), "lens.id"),
        (lambda: BriefLens(challenge_conclusions=1), "lens.challenge_conclusions"),
        (lambda: BriefOutput(ResearchMode.QUICK, language="it"), "output.language"),
        (
            lambda: BriefOutput(ResearchMode.QUICK, preferred_sections=("a", "a")),
            "output.preferred_sections",
        ),
        (
            lambda: BriefOutput(ResearchMode.QUICK, model_profile_id="unresolved"),
            "output.model_profile_id",
        ),
        (lambda: BriefLimits(max_collection_seconds=241), "limits.max_collection_seconds"),
        (lambda: BriefMonitoring(review_conditions=(" ",)), "monitoring.review_conditions"),
        (
            lambda: BriefMonitoring(
                indicators=(BriefIndicator("one", "A"), BriefIndicator("one", "B"))
            ),
            "monitoring.indicators",
        ),
        (lambda: BriefScope(country_isos=("XX",)), "scope.country_isos"),
        (lambda: BriefScope(focus=ResearchFocus.COMPANY), "scope.subject"),
        (lambda: BriefScope(reviewed_aliases=("Unreviewed name",)), "scope.reviewed_aliases"),
        (lambda: BriefScope(map_view_id=BRIEF_ID), "scope.map_revision_id"),
        (lambda: BriefScope(parent_report_id=REPORT_ID), "scope.parent_version"),
        (lambda: BriefScope(disclose_area_to_provider=1), "scope.disclose_area_to_provider"),
        (lambda: BriefCollection(languages=("en", "EN")), "collection.languages"),
        (lambda: BriefCollection(terms=("x" * 301,)), "collection.terms"),
        (lambda: BriefCollection(terms=("x" * 250,) * 5), "collection.terms"),
        (
            lambda: BriefCollection(source_policy="selected_only", source_ids=("news", "news")),
            "collection.source_ids",
        ),
        (
            lambda: BriefCollection(query_variants=(QueryVariant("fr", ("énergie",)),)),
            "collection.query_variants",
        ),
        (lambda: BriefCollection(source_policy="bogus"), "collection.source_policy"),
        (lambda: BriefCollection(web_search=1), "collection.web_search"),
        (
            lambda: BriefPrivateInput("durable_report", report_id=REPORT_ID),
            "private_inputs.report_version",
        ),
        (
            lambda: BriefPrivateInput(
                "session", input_id=INPUT_ID, expires_at=datetime(2026, 9, 1)
            ),
            "private_inputs.expires_at",
        ),
        (lambda: BriefPrivateInput("unknown"), "private_inputs.kind"),
    ],
)
def test_invalid_fields_have_safe_field_addresses(
    factory: Callable[[], object], field: str
) -> None:
    with pytest.raises(BriefValidationError) as caught:
        factory()
    assert caught.value.field == field


@pytest.mark.parametrize("policy", ["explicit", "relative", "template_default", "unknown"])
def test_observation_policy_rejects_mixed_or_missing_intervals(policy: str) -> None:
    kwargs = {
        "explicit": {"since": WHEN, "until": WHEN},
        "relative": {"lookback_hours": 24, "until": WHEN},
        "template_default": {"lookback_hours": 24},
        "unknown": {},
    }
    with pytest.raises(BriefValidationError):
        BriefObservation(policy, **kwargs[policy])


def test_recorded_focus_and_private_collection_are_rejected_at_aggregate_boundary() -> None:
    with pytest.raises(BriefValidationError) as caught:
        brief(
            scope=BriefScope(focus=ResearchFocus.COMPANY, subject="Acme"),
            observation=BriefObservation(
                "explicit",
                since=WHEN - timedelta(days=1),
                until=WHEN,
                time_basis=EvidenceTimeBasis.RECORDED,
            ),
        )
    assert caught.value.field == "observation.time_basis"
    with pytest.raises(BriefValidationError) as caught:
        brief(scope=BriefScope(focus=ResearchFocus.DOCUMENT))
    assert caught.value.field == "private_inputs"
    private = BriefPrivateInput("session", input_id=INPUT_ID)
    with pytest.raises(BriefValidationError) as caught:
        brief(private_inputs=(private, private))
    assert caught.value.field == "private_inputs"


def test_revision_and_admission_require_aware_advancing_clocks() -> None:
    source = brief()
    for at in (WHEN, datetime(2026, 9, 2)):
        with pytest.raises(BriefValidationError) as caught:
            source.revise(at=at)
        assert caught.value.field == "revised_at"
    with pytest.raises(BriefValidationError) as caught:
        source.revise(at=WHEN + timedelta(seconds=1), identity=source.identity)
    assert caught.value.field == "identity"
    for check in (source.require_live_inputs, source.require_subscription_ready):
        with pytest.raises(BriefValidationError) as caught:
            check(now=datetime(2026, 9, 1))
        assert caught.value.field == "observation"


def test_saved_payload_rejects_type_coercion_non_json_and_oversize_before_use() -> None:
    stored = brief_to_dict(brief())
    stored["identity"]["revision"] = True
    with pytest.raises(BriefValidationError):
        brief_from_dict(stored)
    with pytest.raises(BriefValidationError) as caught:
        brief_from_dict([])
    assert caught.value.field == "brief"
    stored = brief_to_dict(brief())
    stored["unknown"] = float("nan")
    with pytest.raises(BriefValidationError) as caught:
        brief_from_dict(stored)
    assert caught.value.field == "brief"
    stored["unknown"] = "x" * MAX_BRIEF_BYTES
    with pytest.raises(BriefValidationError, match="size budget"):
        brief_from_dict(stored)


def test_saved_payload_preserves_nested_field_without_echoing_private_input() -> None:
    stored = brief_to_dict(brief())
    stored["question"]["main"] = "x" * 2400
    with pytest.raises(BriefValidationError) as caught:
        brief_from_dict(stored)
    assert caught.value.field == "question.main"
    assert "x" not in str(caught.value)


def test_legacy_defaults_remain_unset_and_explicit_interval_is_preserved() -> None:
    old = ReportRequest(
        template_id="ask", question="What changed?", research_mode=ResearchMode.QUICK
    )
    converted = brief_from_legacy_request(
        old, brief_id=BRIEF_ID, owner_id=OWNER_ID, title="Simple", created_at=WHEN
    )
    assert converted.observation.policy == "template_default"
    assert converted.observation.lookback_hours is None
    assert legacy_request_from_brief(converted) == old
    historical = replace(
        old,
        research_since=WHEN - timedelta(days=30),
        research_until=WHEN,
        research_time_basis=EvidenceTimeBasis.RECORDED,
    )
    converted_history = brief_from_legacy_request(
        historical, brief_id=BRIEF_ID, owner_id=OWNER_ID, title="History", created_at=WHEN
    )
    assert converted_history.observation.resolved_interval(WHEN) == (
        historical.research_since,
        historical.research_until,
    )
    assert legacy_request_from_brief(converted_history) == historical


def test_legacy_bridge_refuses_non_question_request_and_new_monitoring() -> None:
    with pytest.raises(BriefValidationError) as caught:
        brief_from_legacy_request(
            ReportRequest(template_id="ask"),
            brief_id=BRIEF_ID,
            owner_id=OWNER_ID,
            title="No question",
            created_at=WHEN,
        )
    assert caught.value.field == "question.main"
    with pytest.raises(BriefValidationError, match="canonical admission"):
        legacy_request_from_brief(brief(monitoring=BriefMonitoring(prefer_novelty=True)))
    with pytest.raises(BriefValidationError, match="canonical admission"):
        legacy_request_from_brief(
            brief(
                private_inputs=(BriefPrivateInput("session", input_id=INPUT_ID, expires_at=WHEN),)
            )
        )


def test_authorised_limit_resolution_rejects_unavailable_and_lower_caps() -> None:
    source = brief()
    with pytest.raises(BriefValidationError) as caught:
        resolve_brief_limits(source, BriefAuthorisedCaps(2, 32, 0, 256_000, 240))
    assert caught.value.field == "limits"
    limited = replace(source, limits=BriefLimits(max_model_calls=10))
    with pytest.raises(BriefValidationError) as caught:
        resolve_brief_limits(limited, BriefAuthorisedCaps(2, 32, 9, 256_000, 240))
    assert caught.value.field == "limits.max_model_calls"
