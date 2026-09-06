"""Research monitoring compares frozen structure rather than model prose or labels."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.domain.doctrine import Confidence
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.reports import ReportBody, ReportStatus
from ase.domain.research_changes import change_from_dict, change_to_dict, compare_reports
from ase.domain.validation import Finding, Severity
from evidence_matrix_helpers import item, judgement
from report_documents_helpers import document_records


def versions():
    _, original = document_records()
    evidence = (item("E1"), item("E2"))
    body = ReportBody(key_judgements=(judgement("E1", opposition=("E2",)),))
    original = replace(
        original,
        evidence=evidence,
        body=body,
        findings=(),
        assessment=build_report_assessment(body, evidence, ()),
    )
    return original, replace(original, id=uuid4(), report_id=uuid4())


def test_baseline_and_failed_reports_are_not_changes():
    previous, current = versions()
    baseline = compare_reports(None, current)
    assert baseline.status == "baseline" and baseline.baseline_version_id == current.id
    failed = compare_reports(previous, replace(current, status=ReportStatus.FAILED))
    assert failed.status == "unavailable" and failed.baseline_version_id == previous.id
    assert change_from_dict(change_to_dict(failed)) == failed
    assert change_from_dict(None) is None and change_to_dict(None) is None


def test_prose_judgement_order_and_renumbered_citations_do_not_notify():
    previous, current = versions()
    evidence = tuple(
        replace(value, label=f"R{index}") for index, value in enumerate(current.evidence)
    )
    body = ReportBody(
        key_judgements=(
            replace(
                current.body.key_judgements[0],
                id="KJ99",
                statement="The model rephrased this claim",
                supporting_evidence=("R0",),
                contradicting_evidence=("R1",),
            ),
        )
    )
    current = replace(
        current,
        evidence=tuple(reversed(evidence)),
        body=body,
        assessment=build_report_assessment(body, evidence, ()),
        markdown="Entirely different wording",
    )
    assert compare_reports(previous, current).status == "unchanged"


def test_inventory_hash_and_source_flags_are_explicit_differences():
    previous, current = versions()
    current = replace(
        current,
        evidence=(
            replace(current.evidence[0], content_hash="updated", flags=("source-correction",)),
            item("E3"),
        ),
    )
    change = compare_reports(previous, current)
    assert (change.added, change.removed, change.updated) == (1, 1, 1)
    assert "source_flags_changed" in change.reasons
    assert "evidence_inventory_changed" in change.reasons
    assert "factual accuracy" in change.summary


def test_relationship_reversal_is_a_change_without_claim_text_comparison():
    previous, current = versions()
    body = ReportBody(key_judgements=(judgement("E2", opposition=("E1",)),))
    current = replace(
        current, body=body, assessment=build_report_assessment(body, current.evidence, ())
    )
    assert "evidence_relationships_changed" in compare_reports(previous, current).reasons


def test_engine_confidence_and_validation_changes_notify_but_finding_rephrases_do_not():
    previous, current = versions()
    assessment = current.assessment
    changed = replace(assessment.judgements[0], final_confidence=Confidence.LOW)
    if assessment.judgements[0].final_confidence is Confidence.LOW:
        changed = replace(changed, final_confidence=Confidence.MODERATE)
    current = replace(current, assessment=replace(assessment, judgements=(changed,)))
    assert "engine_confidence_changed" in compare_reports(previous, current).reasons
    finding = Finding("citation", Severity.WARNING, "E1", "Original words")
    previous = replace(previous, findings=(finding,))
    current = replace(previous, id=uuid4(), findings=(replace(finding, message="Rephrased"),))
    assert compare_reports(previous, current).status == "unchanged"
    current = replace(current, findings=())
    assert "validation_findings_changed" in compare_reports(previous, current).reasons


def test_assessment_absence_is_recorded_without_invented_legacy_confidence():
    previous, current = versions()
    change = compare_reports(replace(previous, assessment=None), current)
    assert "assessment_availability_changed" in change.reasons


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "invented"),
        ("added", 1001),
        ("added", True),
        ("reasons", ["arbitrary"]),
        ("report_id", None),
    ],
)
def test_saved_summary_rejects_unbounded_or_unknown_fields(field, value):
    _, current = versions()
    saved = change_to_dict(compare_reports(None, current))
    with pytest.raises(ValueError):
        change_from_dict({**saved, field: value})
