"""Confidence notifications distinguish recorded scores from their changing evidence keys."""

from dataclasses import replace

from ase.domain.doctrine import Confidence
from ase.domain.research_changes import compare_reports
from test_research_changes import versions


def changed(*, confidence):
    before, after = versions()
    old = replace(before.assessment.judgements[0], final_confidence=Confidence.HIGH)
    before = replace(before, assessment=replace(before.assessment, judgements=(old,)))
    new = replace(
        old, supporting_labels=("E2",), contradicting_labels=("E1",), final_confidence=confidence
    )
    after = replace(after, assessment=replace(after.assessment, judgements=(new,)))
    return before, after


def test_support_and_recorded_confidence_change_both_remain_visible():
    result = compare_reports(*changed(confidence=Confidence.LOW))
    assert "evidence_relationships_changed" in result.reasons
    assert "engine_confidence_changed" in result.reasons


def test_link_only_change_does_not_claim_recorded_confidence_change():
    result = compare_reports(*changed(confidence=Confidence.HIGH))
    assert "evidence_relationships_changed" in result.reasons
    assert "engine_confidence_changed" not in result.reasons


def test_unchanged_distinct_link_sets_retain_score_swap_detection():
    before, after = versions()
    first = replace(before.assessment.judgements[0], final_confidence=Confidence.HIGH)
    second = replace(
        first,
        judgement_id="KJ2",
        supporting_labels=("E2",),
        contradicting_labels=("E1",),
        final_confidence=Confidence.LOW,
    )
    before = replace(before, assessment=replace(before.assessment, judgements=(first, second)))
    after = replace(
        after,
        assessment=replace(
            after.assessment,
            judgements=(
                replace(first, final_confidence=Confidence.LOW),
                replace(second, final_confidence=Confidence.HIGH),
            ),
        ),
    )
    reasons = compare_reports(before, after).reasons
    assert "evidence_relationships_changed" not in reasons
    assert "engine_confidence_changed" in reasons
