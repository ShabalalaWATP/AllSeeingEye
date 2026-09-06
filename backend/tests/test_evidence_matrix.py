"""Evidence contribution is qualitative, reproducible and resistant to weak padding."""

from dataclasses import asdict, replace
from itertools import permutations

import pytest

from ase.application.reports.prompts import compose_messages
from ase.application.reports.templates import TEMPLATES
from ase.domain.doctrine import Confidence
from ase.domain.evidence import quality_of_information
from ase.domain.evidence_matrix import Contribution, contribution_for, evidence_policy_metadata
from ase.domain.judgement_assessment import assess_judgement, build_report_assessment
from ase.domain.reports import ReportBody
from ase.domain.validation import Finding, Severity, validate_body
from evidence_matrix_helpers import copy, item, judgement
from feeds_helpers import NOW


@pytest.mark.parametrize(
    "reliability,expected",
    [
        ("A", "strong strong moderate limited limited unassessed"),
        ("B", "strong strong moderate limited limited unassessed"),
        ("C", "moderate moderate limited limited limited unassessed"),
        ("D", "moderate limited limited limited limited unassessed"),
        ("E", "moderate limited limited limited limited unassessed"),
        ("F", "moderate moderate limited limited limited unassessed"),
    ],
)
def test_all_grade_cells_keep_information_credibility_separate(reliability, expected):
    assert [contribution_for(reliability, c).value for c in range(1, 7)] == expected.split()


@pytest.mark.parametrize("grade,credibility", [("", 1), ("AB", 1), ("G", 2), ("A", 0), ("B", 7)])
def test_invalid_grade_metadata_cannot_supply_support(grade, credibility):
    assert contribution_for(grade, credibility) is Contribution.UNASSESSED


def test_single_strong_beats_three_weak_items_and_weak_padding_does_not_help():
    strong = item("E1")
    weak = [item(f"E{i}", "E3") for i in range(2, 5)]
    assert assess_judgement(judgement("E1"), [strong]).confidence_ceiling is Confidence.MODERATE
    assert assess_judgement(judgement("E2", "E3", "E4"), weak).confidence_ceiling is Confidence.LOW
    assert (
        assess_judgement(judgement("E1", "E2", "E3", "E4"), [strong, *weak]).confidence_ceiling
        is Confidence.MODERATE
    )
    moderate = item("E1", "F2")
    assert (
        assess_judgement(judgement("E1", "E2", "E3", "E4"), [moderate, *weak]).confidence_ceiling
        is Confidence.LOW
    )


def test_unknown_reliability_can_contribute_but_unknown_provenance_cannot_corroborate():
    known = [item("E1", "F1"), item("E2", "E1")]
    assert assess_judgement(judgement("E1", "E2"), known).confidence_ceiling is Confidence.MODERATE
    unknown = [replace(i, independence_key="") for i in known]
    assert assess_judgement(judgement("E1", "E2"), unknown).confidence_ceiling is Confidence.LOW
    assert (
        assess_judgement(judgement("E1"), [item("E1", "A2", "")]).confidence_ceiling
        is Confidence.MODERATE
    )


def test_copies_parent_groups_and_repeated_labels_count_only_once():
    first = item("E1", "A1")
    second = copy(first, "E2", "other publisher")
    for second_ in (second, replace(second, content_hash="different"), item("E2", "A1", "E1")):
        result = assess_judgement(judgement("E1", "E1", "E2"), [first, second_])
        assert len(result.support_groups) == 1
        assert result.confidence_ceiling is Confidence.MODERATE
        assert result.supporting_labels == ("E1", "E2")


def test_translated_copy_titles_fold_together():
    first = replace(
        item("E1", "A1"), title="都市で部隊が移動", title_en="Units leave northern camp"
    )
    second = replace(item("E2", "B1"), title="Units leave northern camp")
    result = assess_judgement(judgement("E1", "E2"), [first, second])
    assert len(result.support_groups) == 1 and result.support_groups[0].possible_copy
    assert result.confidence_ceiling is Confidence.MODERATE


def test_weak_known_copy_cannot_lend_its_provenance_to_unknown_strong_support():
    known = item("E1", "C2")
    unknown = item("E2", "A2", "")
    weak_copy = replace(copy(unknown, "E3", "known weak outlet"), reliability="E", credibility=6)
    result = assess_judgement(judgement("E1", "E2", "E3"), [known, unknown, weak_copy])
    unknown_group = next(group for group in result.support_groups if "E2" in group.labels)
    assert unknown_group.contribution is Contribution.STRONG
    assert unknown_group.corroborating_contribution is Contribution.UNASSESSED
    assert (
        sum(g.corroborating_contribution is Contribution.MODERATE for g in result.support_groups)
        == 1
    )


def test_high_needs_two_known_confirmed_strong_groups_and_flags_never_help():
    strong = [item("E1", "A1"), item("E2", "B1")]
    kj = judgement("E1", "E2")
    assert assess_judgement(kj, strong).confidence_ceiling is Confidence.HIGH
    for weaker in (
        [replace(i, credibility=2) for i in strong],
        [item("E1", "F1"), item("E2", "E1")],
    ):
        assert assess_judgement(kj, weaker).confidence_ceiling is Confidence.MODERATE
    flagged = [replace(strong[0], flags=("interested_party",)), strong[1]]
    assert assess_judgement(kj, flagged).confidence_ceiling is Confidence.MODERATE


@pytest.mark.parametrize(
    "opposing_grade,expected",
    [("A2", Confidence.LOW), ("C2", Confidence.MODERATE), ("E6", Confidence.MODERATE)],
)
def test_opposition_strength_changes_ceiling_without_disappearing(opposing_grade, expected):
    evidence = [item("E1", "A1"), item("E2", "B1"), item("E3", opposing_grade)]
    result = assess_judgement(judgement("E1", "E2", opposition=("E3",)), evidence)
    assert result.confidence_ceiling is expected
    assert result.contradicting_labels == ("E3",) and result.status == "contested"
    assert any("Model-assigned opposition" in reason for reason in result.explanation)


def test_support_and_opposition_use_shared_copy_groups_without_double_corroboration():
    first = item("E1", "A1")
    result = assess_judgement(
        judgement("E1", opposition=("E2",)), [first, copy(first, "E2", "other")]
    )
    assert result.support_groups[0].id == result.opposition_groups[0].id
    assert result.confidence_ceiling is Confidence.LOW


def test_permutation_and_unrelated_pool_do_not_change_judgement_assessment():
    evidence = [item("E1", "A1"), item("E2", "B1"), item("E3", "E6")]
    kj = judgement("E1", "E2")
    expected = assess_judgement(kj, evidence[:2])
    assert all(assess_judgement(kj, order) == expected for order in permutations(evidence))
    validated = validate_body(
        ReportBody(key_judgements=(kj,)), frozenset(), {}, evidence_items=evidence
    )
    assert validated.body.key_judgements[0].confidence is Confidence.HIGH
    capped = validate_body(
        ReportBody(key_judgements=(kj,)),
        frozenset(),
        {},
        evidence_items=evidence,
        confidence_ceiling=Confidence.LOW,
    )
    assert capped.body.key_judgements[0].confidence is Confidence.LOW


def test_empty_invalid_and_overlapping_citations_fail_closed_and_remain_explained():
    empty = assess_judgement(judgement("missing"), [])
    assert empty.confidence_ceiling is Confidence.LOW and empty.status == "unsupported"
    assert empty.invalid_labels == ("missing",) and empty.improvements
    overlap = assess_judgement(judgement("E1", opposition=("E1",)), [item("E1")])
    assert overlap.confidence_ceiling is Confidence.LOW


def test_final_assessment_preserves_final_confidence_and_reports_counts_and_limitations():
    body = ReportBody(key_judgements=(replace(judgement("E1"), confidence=Confidence.LOW),))
    findings = [
        Finding("citation", Severity.ERROR, "KJ1", "Invalid"),
        Finding("style", Severity.WARNING, "KJ1", "Style"),
    ]
    result = build_report_assessment(body, [item("E1"), item("E2", "F6", "")], findings)
    assert result.method_version == "ase-evidence-v1"
    assert result.judgements[0].confidence_ceiling is Confidence.MODERATE
    assert result.judgements[0].final_confidence is Confidence.LOW
    assert result.tallies.strong == 1 and result.tallies.unassessed == 1
    assert result.tallies.supported_judgements == 1
    assert result.validation_errors == 1 and result.validation_warnings == 1
    assert "not an official NATO" in " ".join(result.limitations)
    assert "devil's advocacy" in " ".join(result.limitations)
    assert asdict(build_report_assessment(ReportBody(), [], []))["evidence"] == ()


def test_metadata_and_prompt_disclose_policy_without_whole_bundle_limit():
    metadata = evidence_policy_metadata()
    assert len(metadata["contribution_matrix"]) == 36
    assert len(metadata["reliability_scale"]) == 6 and len(metadata["credibility_scale"]) == 6
    assert all(ref["url"].startswith("https://") for ref in metadata["doctrine_references"])
    messages = compose_messages(
        TEMPLATES["intsum"],
        scope_line="Test",
        period_from=NOW,
        period_to=NOW,
        question=None,
        quality=quality_of_information([item("E1", "E6")]),
        evidence=[item("E1", "E6")],
    )
    assert "Confidence may not exceed" not in messages[1].content
    assert "limited separately for each judgement" in messages[1].content
    assert "Application evidence contribution: unassessed" in messages[1].content
