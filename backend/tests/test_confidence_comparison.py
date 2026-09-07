"""Frozen confidence explanations require explicit or unique exact-statement correspondence."""

from dataclasses import replace

import pytest

from annotation_comparison_helpers import side
from ase.domain.annotation_comparison import JudgementCorrespondence
from ase.domain.confidence_comparison import confidence_deltas
from ase.domain.doctrine import Confidence
from ase.domain.judgement_assessment import build_report_assessment
from test_research_changes import versions


def test_simultaneous_support_and_score_changes_have_separate_frozen_explanations():
    previous, current = versions()
    old = replace(previous.assessment.judgements[0], final_confidence=Confidence.HIGH)
    new = replace(
        old,
        supporting_labels=("E2",),
        contradicting_labels=("E1",),
        final_confidence=Confidence.LOW,
    )
    previous = replace(previous, assessment=replace(previous.assessment, judgements=(old,)))
    current = replace(current, assessment=replace(current.assessment, judgements=(new,)))
    (delta,) = confidence_deltas(side(previous), side(current), ())
    assert delta.correspondence == "exact_statement"
    assert {"supporting_evidence", "final_confidence"}.issubset(delta.changed_fields)
    assert any("high to low" in text for text in delta.explanations)
    assert any("not a uniquely established cause" in text for text in delta.explanations)


def test_reused_judgement_id_with_different_statement_is_not_correspondence():
    previous, current = versions()
    judgement = current.body.key_judgements[0]
    current = replace(
        current,
        body=replace(
            current.body,
            key_judgements=(replace(judgement, statement="A wholly different assertion."),),
        ),
    )
    changes = confidence_deltas(side(previous), side(current), ())
    assert [row.status for row in changes] == ["removed", "added"]
    assert all(row.correspondence == "unmatched" for row in changes)
    declared = (
        JudgementCorrespondence(judgement.id, judgement.id, "Operator-declared conceptual link"),
    )
    assert (
        confidence_deltas(side(previous), side(current), declared)[0].correspondence
        == "operator_declared"
    )


def test_relabelling_and_group_id_changes_do_not_invent_confidence_changes():
    previous, current = versions()
    evidence = tuple(
        replace(item, label=f"R{index}") for index, item in enumerate(current.evidence)
    )
    judgement = replace(
        current.body.key_judgements[0],
        id="KJ7",
        supporting_evidence=("R0",),
        contradicting_evidence=("R1",),
    )
    body = replace(current.body, key_judgements=(judgement,))
    current = replace(
        current,
        evidence=evidence,
        body=body,
        assessment=build_report_assessment(body, evidence, ()),
    )
    (delta,) = confidence_deltas(side(previous), side(current), ())
    assert delta.status == "unchanged" and delta.changed_fields == ()


@pytest.mark.parametrize(
    "fault", ["missing_assessment", "missing_row", "invalid_label", "unknown_support"]
)
def test_unavailable_or_incomplete_frozen_assessment_does_not_invent_confidence(fault):
    previous, current = versions()
    assessment = current.assessment
    if fault == "missing_assessment":
        assessment = None
    elif fault == "missing_row":
        assessment = replace(assessment, evidence=assessment.evidence[1:])
    elif fault == "invalid_label":
        assessment = replace(
            assessment, judgements=(replace(assessment.judgements[0], invalid_labels=("E999",)),)
        )
    else:
        assessment = replace(
            assessment, judgements=(replace(assessment.judgements[0], supporting_labels=("E999",)),)
        )
    (delta,) = confidence_deltas(side(previous), side(replace(current, assessment=assessment)), ())
    assert delta.changed_fields == ("assessment_availability",)
    assert "no confidence direction" in " ".join(delta.explanations)


def test_method_change_is_explained_without_recomputing_old_grade():
    previous, current = versions()
    current = replace(
        current, assessment=replace(current.assessment, method_version="future-method")
    )
    (delta,) = confidence_deltas(side(previous), side(current), ())
    assert delta.changed_fields == ("method_version",)
    assert "not recomputed" in " ".join(delta.explanations)


def test_ambiguous_identical_statements_require_explicit_correspondence():
    previous, current = versions()
    body = replace(
        previous.body,
        key_judgements=(
            previous.body.key_judgements[0],
            replace(previous.body.key_judgements[0], id="KJ2"),
        ),
    )
    changes = confidence_deltas(side(replace(previous, body=body)), side(current), ())
    assert all(row.correspondence == "unmatched" for row in changes)
