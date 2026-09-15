from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.api.schemas_subscription_editions import EditionComparisonOut
from ase.application.reports.subscription_comparison import compare_subscription_versions
from ase.domain.doctrine import Confidence, Probability
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.evidence_attributes import EvidenceAttribute
from ase.domain.report_records import ReportVersion
from ase.domain.reports import KeyJudgement, ReportBody, ReportStatus
from ase.domain.research_changes import ChangeClassification, ComparisonReason, ComparisonState
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import EditionCoverage

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


def evidence(
    identity: str = "one", *, digest: str = "a" * 64, previous: str | None = None
) -> EvidenceItem:
    attributes = (
        EvidenceAttribute("original_sha256", digest),
        EvidenceAttribute("canonical_url", "https://official.example/report"),
        *((EvidenceAttribute("previous_sha256", previous),) if previous else ()),
    )
    return EvidenceItem(
        "E1",
        identity,
        "official",
        "Official source",
        "official",
        "economic",
        "Release",
        "Release detail",
        "https://official.example/report",
        NOW,
        NOW,
        "B1",
        "usually reliable",
        3,
        "Recorded source",
        None,
        None,
        "GB",
        digest,
        attributes=attributes,
    )


def version(
    *,
    probability: Probability = Probability.UNLIKELY,
    item: EvidenceItem | None = None,
    status: ReportStatus = ReportStatus.READY,
) -> ReportVersion:
    item = item or evidence()
    judgement = KeyJudgement(
        "KJ1",
        "The assessed outcome remains bounded.",
        probability,
        Confidence.MODERATE,
        "Evidence is limited.",
        ("E1",),
        (),
        ("assumption-1",),
        indicators=("watch-1",),
    )
    return ReportVersion(
        uuid4(),
        uuid4(),
        1,
        status,
        ReportBody(key_judgements=(judgement,)),
        (),
        (item,),
        QualityOfInformation(1),
        "",
        None,
        "test",
        1,
        1,
        1,
        1,
        NOW,
    )


def test_likelihood_only_change_is_an_assessment_change() -> None:
    previous = version()
    current = version(probability=Probability.LIKELY)

    result = compare_subscription_versions(
        previous, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )

    assert result.state is ComparisonState.ASSESSMENT_CHANGED
    assert result.reasons == (ComparisonReason.LIKELIHOOD_CHANGED,)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("supporting_evidence", (), ComparisonReason.SUPPORT_CHANGED),
        ("assumptions", ("revised-assumption",), ComparisonReason.ASSUMPTIONS_CHANGED),
        ("indicators", ("revised-watch",), ComparisonReason.INDICATORS_CHANGED),
    ),
)
def test_stable_claim_dimension_changes_survive_exact_report_projection(
    field: str, value: tuple[str, ...], reason: ComparisonReason
) -> None:
    previous = version()
    current = version(item=previous.evidence[0])
    old_claim = current.body.key_judgements[0]
    current = replace(
        current,
        body=replace(
            current.body,
            key_judgements=(replace(old_claim, **{field: value}),),
        ),
    )

    result = compare_subscription_versions(
        previous, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )

    assert result.state is ComparisonState.ASSESSMENT_CHANGED
    assert result.reasons == (reason,)
    assert result.changed_claim_ids == ("KJ1",)


def test_swapped_report_claim_text_requires_mapping_review() -> None:
    previous = version()
    first = previous.body.key_judgements[0]
    second = replace(first, id="KJ2", statement="A distinct judgement.")
    previous = replace(previous, body=replace(previous.body, key_judgements=(first, second)))
    current = version(item=previous.evidence[0])
    current = replace(
        current,
        body=replace(
            current.body,
            key_judgements=(
                replace(first, statement=second.statement),
                replace(second, statement=first.statement),
            ),
        ),
    )

    result = compare_subscription_versions(
        previous, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert result.reasons == (ComparisonReason.CLAIM_MAPPING_UNRESOLVED,)
    assert result.changed_claim_ids == ("KJ1", "KJ2")


def test_explicit_same_url_original_correction_preserves_version_link() -> None:
    previous = version(item=evidence(digest="a" * 64))
    current = version(item=evidence("two", digest="b" * 64, previous="a" * 64))

    result = compare_subscription_versions(
        previous, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )

    assert result.state is ComparisonState.SIGNIFICANT_CONTRADICTION_OR_CORRECTION
    assert result.reasons[:2] == (
        ComparisonReason.SUPPORT_CHANGED,
        ComparisonReason.SOURCE_CORRECTION,
    )
    assert result.corrected_evidence_ids == ("official:two",)


def test_failure_precedes_inadequate_coverage() -> None:
    result = compare_subscription_versions(
        version(),
        version(status=ReportStatus.FAILED),
        EditionCoverage.PARTIAL,
        baseline_expected=True,
    )

    assert result.state is ComparisonState.FAILURE
    assert result.reasons[:2] == (
        ComparisonReason.CURRENT_RUN_FAILED,
        ComparisonReason.COVERAGE_INADEQUATE,
    )


def test_quiet_requires_complete_coverage_and_a_loaded_expected_baseline() -> None:
    previous = version()
    current = replace(version(), body=previous.body, evidence=previous.evidence)
    quiet = compare_subscription_versions(
        previous, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )
    missing = compare_subscription_versions(
        None, current, EditionCoverage.COMPLETE_FOR_PLAN, baseline_expected=True
    )

    assert quiet.state is ComparisonState.NO_NEW_RELEVANT_EVIDENCE
    assert missing.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert ComparisonReason.BASELINE_UNAVAILABLE in missing.reasons


def test_changed_brief_is_an_incompatible_limited_comparison() -> None:
    result = compare_subscription_versions(
        None,
        version(),
        EditionCoverage.COMPLETE_FOR_PLAN,
        baseline_expected=True,
        baseline_compatible=False,
    )

    assert result.state is ComparisonState.INSUFFICIENT_COVERAGE
    assert result.reasons[:2] == (
        ComparisonReason.BASELINE_UNAVAILABLE,
        ComparisonReason.BASELINE_INCOMPATIBLE,
    )


def test_unresolved_claim_mapping_is_explained_in_history() -> None:
    previous = version()
    current = version()
    comparison = EditionComparison(
        uuid4(),
        previous.id,
        current.id,
        ChangeClassification(
            ComparisonState.INSUFFICIENT_COVERAGE,
            (ComparisonReason.CLAIM_MAPPING_UNRESOLVED,),
            changed_claim_ids=("KJ1",),
        ),
        NOW,
    )

    projected = EditionComparisonOut.from_comparison(comparison)

    assert "claim mapping" in projected.summary.lower()
    assert "review" in projected.summary.lower()
