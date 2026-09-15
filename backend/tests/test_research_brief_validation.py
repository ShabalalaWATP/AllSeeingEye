"""Field-addressed validation protects authored and persisted brief boundaries."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_brief_scope import (
    BriefCollection,
    BriefObservation,
    BriefPrivateInput,
    BriefScope,
)
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
)
from ase.domain.research_plan import QueryVariant

BRIEF_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
REPORT_ID = UUID("44444444-4444-4444-8444-444444444444")
INPUT_ID = UUID("55555555-5555-4555-8555-555555555555")
WHEN = datetime(2026, 9, 1, tzinfo=UTC)


def identity() -> BriefIdentity:
    return BriefIdentity(BRIEF_ID, 1, OWNER_ID, "Brief", WHEN, WHEN)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda: replace(identity(), schema_version=True), "schema_version"),
        (lambda: replace(identity(), team_id="unresolved"), "team_id"),
        (lambda: replace(identity(), origin="unknown"), "origin"),
        (lambda: replace(identity(), revised_at=WHEN - timedelta(seconds=1)), "revised_at"),
        (lambda: BriefQuestion("Main", exclusions=("Skip",) * 11), "question.exclusions"),
        (lambda: BriefOutput("unsupported"), "output.depth"),
        (lambda: BriefOutput(ResearchMode.QUICK, style="unsupported"), "output.style"),
        (
            lambda: BriefOutput(
                ResearchMode.QUICK, preferred_sections=tuple(f"s{i}" for i in range(17))
            ),
            "output.preferred_sections",
        ),
        (lambda: BriefOutput(ResearchMode.QUICK, chart_preference="unsupported"), "output.visuals"),
        (
            lambda: BriefMonitoring(review_conditions=("Review",) * 9),
            "monitoring.review_conditions",
        ),
        (lambda: BriefMonitoring(prefer_novelty=1), "monitoring.prefer_novelty"),
        (
            lambda: BriefMonitoring(organisation_profile_id="unresolved"),
            "monitoring.organisation_profile_id",
        ),
        (lambda: BriefScope(country_isos=["GB"]), "scope.country_isos"),
        (lambda: BriefScope(focus="unsupported"), "scope.focus"),
        (
            lambda: BriefScope(country_isos=("GB",), focus=ResearchFocus.COMPANY, subject="Acme"),
            "scope.country_isos",
        ),
        (
            lambda: BriefScope(subject="Acme", reviewed_aliases=("Alias",) * 17),
            "scope.reviewed_aliases",
        ),
        (lambda: BriefScope(categories=("invalid",)), "scope.categories"),
        (lambda: BriefScope(map_origin="unresolved"), "scope.map_origin"),
        (lambda: BriefScope(map_view_id=BRIEF_ID, map_revision_id="bad"), "scope.map_view_id"),
        (lambda: BriefScope(plan_id="unresolved"), "scope.plan_id"),
        (lambda: BriefScope(parent_report_id="bad", parent_version=1), "scope.parent_report_id"),
        (
            lambda: BriefObservation("relative", lookback_hours=24, time_basis="unsupported"),
            "observation.time_basis",
        ),
        (
            lambda: BriefObservation("relative", lookback_hours=24, forecast_horizon_days=367),
            "observation.forecast_horizon_days",
        ),
        (lambda: BriefObservation("explicit", since=WHEN), "observation"),
        (lambda: BriefCollection(terms=["query"]), "collection.terms"),
        (
            lambda: BriefCollection(query_variants=[QueryVariant("en", ("query",))]),
            "collection.query_variants",
        ),
        (
            lambda: BriefCollection(source_policy="selected_only", source_ids=["news"]),
            "collection.source_ids",
        ),
        (lambda: BriefPrivateInput("session"), "private_inputs.input_id"),
        (
            lambda: BriefPrivateInput("session", input_id=INPUT_ID, disclose_to_provider=1),
            "private_inputs.disclose_to_provider",
        ),
        (
            lambda: BriefPrivateInput(
                "durable_report", report_id=REPORT_ID, report_version=1, expires_at=WHEN
            ),
            "private_inputs.report_id",
        ),
    ],
)
def test_invalid_authored_fields_identify_the_safe_field(
    factory: Callable[[], object], field: str
) -> None:
    with pytest.raises(BriefValidationError) as caught:
        factory()
    assert caught.value.field == field


def test_template_default_resolves_only_when_an_admission_sets_it() -> None:
    assert BriefObservation("template_default").resolved_interval(WHEN) is None
    with pytest.raises(BriefValidationError) as caught:
        BriefObservation("relative", lookback_hours=24).resolved_interval(datetime(2026, 9, 1))
    assert caught.value.field == "observation"
