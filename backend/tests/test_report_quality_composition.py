"""The gate composes several failed checks at once, and leaves frozen reports alone."""

from dataclasses import replace

from ase.application.reports.claim_export_integrity import export_content_digest
from ase.application.reports.post_draft_checks import mechanical_quality_findings
from ase.application.reports.quality_gate import final_report_status, material_review_reasons
from ase.application.reports.templates import TEMPLATES
from ase.domain.canonical_provenance import canonical_snapshot
from ase.domain.report_quality_rules import (
    DATE_RULE,
    ENTAILMENT_RULE,
    FIGURE_RULE,
    HOUSE_STYLE_RULE,
    REQUIREMENT_GATE_RULE,
    SOURCE_SUFFICIENCY_RULE,
    TEMPLATE_STRUCTURE_RULE,
)
from ase.domain.reports import ReportStatus
from ase.domain.validation_types import Finding, Severity
from report_documents_helpers import document_records

RULES = (
    FIGURE_RULE,
    DATE_RULE,
    HOUSE_STYLE_RULE,
    TEMPLATE_STRUCTURE_RULE,
    SOURCE_SUFFICIENCY_RULE,
    REQUIREMENT_GATE_RULE,
    ENTAILMENT_RULE,
)


def finding(rule: str, severity: Severity = Severity.ERROR) -> Finding:
    return Finding(rule, severity, "KJ1", f"A {rule.replace('_', ' ')} problem was found.")


def test_every_failed_check_appears_as_its_own_reason() -> None:
    findings = tuple(finding(rule) for rule in RULES)
    reasons = material_review_reasons(None, None, None, findings)
    assert len(reasons) == len(RULES)
    assert all(row.message in reasons for row in findings)
    assert (
        final_report_status(ReportStatus.READY, None, None, None, findings)
        is ReportStatus.NEEDS_REVIEW
    )


def test_advisory_findings_and_unrelated_rules_do_not_gate_the_report() -> None:
    advisory = (
        finding(HOUSE_STYLE_RULE, Severity.WARNING),
        finding(ENTAILMENT_RULE, Severity.WARNING),
        Finding("grade", Severity.ERROR, "KJ1", "An unrelated rule."),
    )
    assert material_review_reasons(None, None, None, advisory) == ()
    assert final_report_status(ReportStatus.READY, None, None, None, advisory) is ReportStatus.READY


def test_repeated_messages_are_shown_once() -> None:
    repeated = (finding(FIGURE_RULE), finding(FIGURE_RULE))
    assert len(material_review_reasons(None, None, None, repeated)) == 1


def test_a_failed_report_is_never_promoted_by_a_clean_check_set() -> None:
    assert final_report_status(ReportStatus.FAILED, None, None, None, ()) is ReportStatus.FAILED


def test_checking_a_frozen_report_changes_neither_its_bytes_nor_its_hash() -> None:
    record, version = document_records()
    before = canonical_snapshot(version)
    digest = export_content_digest(record, version)
    findings = mechanical_quality_findings(
        version.body, record.header, TEMPLATES["intsum"], version.evidence
    )
    assert canonical_snapshot(version) == before
    assert export_content_digest(record, version) == digest
    assert all(isinstance(row, Finding) for row in findings)


def test_a_new_check_adds_no_field_to_the_frozen_version() -> None:
    _, version = document_records()
    snapshot = canonical_snapshot(replace(version))
    assert "quality_checks" not in snapshot
    assert set(snapshot) == set(canonical_snapshot(version))
