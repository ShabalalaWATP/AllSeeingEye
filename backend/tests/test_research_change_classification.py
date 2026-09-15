from dataclasses import replace

import pytest

from ase.domain.research_changes import (
    ComparisonClaim,
    ComparisonEvidence,
    ComparisonInput,
    ComparisonReason,
    ComparisonState,
    classify_research_change,
)
from ase.domain.subscription_editions import EditionCoverage

COMPLETE = EditionCoverage.COMPLETE_FOR_PLAN
BASE_CLAIM = ComparisonClaim("claim-1", "meaning-a", likelihood_band="unlikely")
BASE_EVIDENCE = ComparisonEvidence("evidence-1", "hash-a", "original-a")


def comparison(**changes: object) -> ComparisonInput:
    value = ComparisonInput(
        previous_claims=(BASE_CLAIM,),
        current_claims=(BASE_CLAIM,),
        previous_evidence=(BASE_EVIDENCE,),
        current_evidence=(BASE_EVIDENCE,),
        coverage=COMPLETE,
        attempted_providers=("provider-a",),
        successful_providers=("provider-a",),
    )
    return replace(value, **changes)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("meaning_fingerprint", "meaning-b", ComparisonReason.CLAIM_MEANING_CHANGED),
        ("likelihood_band", "likely", ComparisonReason.LIKELIHOOD_CHANGED),
        ("horizon_fingerprint", "2027", ComparisonReason.HORIZON_CHANGED),
        ("support", ("evidence-2",), ComparisonReason.SUPPORT_CHANGED),
        ("opposition", ("evidence-2",), ComparisonReason.OPPOSITION_CHANGED),
        ("assumptions", ("assumption-a",), ComparisonReason.ASSUMPTIONS_CHANGED),
        ("indicators", ("indicator-a",), ComparisonReason.INDICATORS_CHANGED),
    ),
)
def test_each_claim_dimension_changes_the_assessment(
    field: str, value: object, reason: ComparisonReason
) -> None:
    current = replace(BASE_CLAIM, **{field: value})

    result = classify_research_change(comparison(current_claims=(current,)))

    assert result.state is ComparisonState.ASSESSMENT_CHANGED
    assert result.reasons == (reason,)
    assert result.changed_claim_ids == ("claim-1",)


def test_swapped_meanings_leave_claim_mapping_unresolved() -> None:
    old = (ComparisonClaim("a", "first"), ComparisonClaim("b", "second"))
    new = (ComparisonClaim("a", "second"), ComparisonClaim("b", "first"))

    result = classify_research_change(comparison(previous_claims=old, current_claims=new))

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert result.reasons == (ComparisonReason.CLAIM_MAPPING_UNRESOLVED,)
    assert result.changed_claim_ids == ("a", "b")


def test_reidentified_claim_is_not_a_definitive_new_assessment() -> None:
    old = (ComparisonClaim("old-id", "same-meaning"),)
    new = (ComparisonClaim("new-id", "same-meaning"),)

    result = classify_research_change(comparison(previous_claims=old, current_claims=new))

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert result.reasons == (
        ComparisonReason.CLAIM_INVENTORY_CHANGED,
        ComparisonReason.CLAIM_MAPPING_UNRESOLVED,
    )
    assert result.changed_claim_ids == ("new-id", "old-id")


def test_actual_meaning_edit_on_stable_id_is_an_assessment_change() -> None:
    old = (ComparisonClaim("a", "first"), ComparisonClaim("b", "second"))
    new = (ComparisonClaim("a", "third"), ComparisonClaim("b", "second"))

    result = classify_research_change(comparison(previous_claims=old, current_claims=new))

    assert result.state is ComparisonState.ASSESSMENT_CHANGED
    assert result.reasons == (ComparisonReason.CLAIM_MEANING_CHANGED,)
    assert result.changed_claim_ids == ("a",)


def test_failure_has_precedence_but_retains_other_reasons() -> None:
    result = classify_research_change(
        comparison(
            current_failed=True,
            baseline_available=False,
            coverage=EditionCoverage.INSUFFICIENT,
            successful_providers=(),
        )
    )

    assert result.state is ComparisonState.FAILURE
    assert result.reasons[:4] == (
        ComparisonReason.CURRENT_RUN_FAILED,
        ComparisonReason.BASELINE_UNAVAILABLE,
        ComparisonReason.PROVIDER_OUTAGE,
        ComparisonReason.COVERAGE_INADEQUATE,
    )


def test_provider_outage_overrides_captured_novelty_without_reporting_quiet() -> None:
    new_evidence = ComparisonEvidence("evidence-2", "new-hash", "new-origin")
    result = classify_research_change(
        comparison(successful_providers=(), current_evidence=(new_evidence,))
    )

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert ComparisonReason.PROVIDER_OUTAGE in result.reasons
    assert ComparisonReason.NEW_RELEVANT_EVIDENCE in result.reasons
    assert ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE not in result.reasons


@pytest.mark.parametrize(
    "changes",
    (
        {"baseline_available": False},
        {"baseline_compatible": False},
        {"coverage": EditionCoverage.PARTIAL},
        {"successful_providers": ()},
    ),
)
def test_quiet_period_requires_compatible_baseline_and_adequate_coverage(
    changes: dict[str, object],
) -> None:
    result = classify_research_change(comparison(**changes))

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE not in result.reasons


def test_quiet_period_is_explainable_when_coverage_is_adequate() -> None:
    result = classify_research_change(comparison())

    assert result.state is ComparisonState.NO_NEW_RELEVANT_EVIDENCE
    assert result.reasons == (ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE,)


def test_syndicated_copies_count_as_one_new_development() -> None:
    copies = tuple(
        ComparisonEvidence(f"copy-{number}", "same-content", "wire-report") for number in range(10)
    )

    result = classify_research_change(comparison(current_evidence=copies))

    assert result.state is ComparisonState.NEW_EVIDENCE_UNCHANGED_ASSESSMENT
    assert result.novel_evidence_ids == ("copy-0",)
    assert len(result.syndicated_duplicate_ids) == 9
    assert ComparisonReason.SYNDICATED_DUPLICATES_ONLY not in result.reasons


def test_mixed_novel_and_syndicated_evidence_is_not_labelled_duplicates_only() -> None:
    items = (
        ComparisonEvidence("new", "translated", "report-a"),
        ComparisonEvidence("copy", "hash-a", "original-a"),
    )

    result = classify_research_change(comparison(current_evidence=items))

    assert result.state is ComparisonState.NEW_EVIDENCE_UNCHANGED_ASSESSMENT
    assert result.novel_evidence_ids == ("new",)
    assert result.syndicated_duplicate_ids == ("copy",)
    assert ComparisonReason.SYNDICATED_DUPLICATES_ONLY not in result.reasons


def test_previously_seen_syndication_is_not_new_evidence() -> None:
    repeated = ComparisonEvidence("publisher-copy", "hash-a", "original-a")

    result = classify_research_change(comparison(current_evidence=(BASE_EVIDENCE, repeated)))

    assert result.state is ComparisonState.NO_NEW_RELEVANT_EVIDENCE
    assert result.syndicated_duplicate_ids == ("publisher-copy",)
    assert ComparisonReason.SYNDICATED_DUPLICATES_ONLY in result.reasons


def test_same_url_is_a_correction_only_with_preserved_version_link() -> None:
    previous = ComparisonEvidence("official-v1", "old-hash", "official", "https://example.test/a")
    linked = ComparisonEvidence(
        "official-v2", "new-hash", "official", "https://example.test/a", "old-hash"
    )
    unlinked = replace(linked, correction_of_hash=None)

    corrected = classify_research_change(
        comparison(previous_evidence=(previous,), current_evidence=(linked,))
    )
    ordinary_update = classify_research_change(
        comparison(previous_evidence=(previous,), current_evidence=(unlinked,))
    )

    assert corrected.state is ComparisonState.SIGNIFICANT_CONTRADICTION_OR_CORRECTION
    assert corrected.corrected_evidence_ids == ("official-v2",)
    assert ComparisonReason.SOURCE_CORRECTION not in ordinary_update.reasons
    assert ordinary_update.state is ComparisonState.NEW_EVIDENCE_UNCHANGED_ASSESSMENT


def test_contradiction_precedes_claim_and_evidence_changes() -> None:
    changed = replace(BASE_CLAIM, likelihood_band="likely", significant_contradiction=True)
    new_evidence = ComparisonEvidence("evidence-2", "hash-b", "original-b")

    result = classify_research_change(
        comparison(current_claims=(changed,), current_evidence=(new_evidence,))
    )

    assert result.state is ComparisonState.SIGNIFICANT_CONTRADICTION_OR_CORRECTION
    assert ComparisonReason.LIKELIHOOD_CHANGED in result.reasons
    assert ComparisonReason.NEW_RELEVANT_EVIDENCE in result.reasons


def test_ambiguous_claim_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="unambiguous"):
        comparison(current_claims=(BASE_CLAIM, BASE_CLAIM))
