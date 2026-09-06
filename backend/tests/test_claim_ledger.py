"""Claim inspection retains frozen decisions and makes missing metadata explicit."""

from dataclasses import replace
from uuid import uuid4

from ase.api.schemas_reports import ReportVersionOut
from ase.domain.citation_checks import (
    CitationCheck,
    CitationStatus,
    FrozenExcerpt,
    JudgementCitationCheck,
    ReportCitationChecks,
)
from ase.domain.claim_ledger import build_claim_ledger
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.reports import Gap, ReportBody
from evidence_matrix_helpers import item, judgement
from report_documents_helpers import document_records


def test_legacy_has_unknown_dimensions_without_inventing_scores() -> None:
    _, version = document_records()
    ledger = build_claim_ledger(version)
    assert ledger.claims
    for claim in ledger.claims:
        assert claim.assessment is None and claim.citation_checks is None
        assert {dimension.status for dimension in claim.dimensions} == {"unknown"}
        assert claim.kind == "analytical_inference"
    assert ReportVersionOut.from_version(version).claim_ledger is not None
    assert version.assessment is None and version.citation_checks is None


def test_ids_are_version_scoped_and_statements_are_not_split() -> None:
    _, version = document_records()
    original = replace(judgement("E1"), statement="Units leave. The camp remains empty.")
    version = replace(version, body=ReportBody(key_judgements=(original,)))
    ledger = build_claim_ledger(version)
    assert len(ledger.claims) == 1
    assert ledger.claims[0].statement == original.statement
    assert ledger.claims[0].id == build_claim_ledger(version).claims[0].id
    other_version = replace(version, id=uuid4(), number=version.number + 1)
    assert ledger.claims[0].id != build_claim_ledger(other_version).claims[0].id


def test_frozen_groups_and_literal_checks_are_preserved_without_rescoring(monkeypatch) -> None:
    _, version = document_records()
    body = ReportBody(
        key_judgements=(judgement("E1", opposition=("E2",)),),
        gaps=(Gap("Original source remains unknown."),),
    )
    evidence = (item("E1", "A1", "Agency"), item("E2", "D4", ""))
    assessment = build_report_assessment(body, evidence, ())
    frozen = replace(assessment.judgements[0], status="unsupported", explanation=("Saved rule.",))
    assessment = replace(assessment, method_version="historic-rule", judgements=(frozen,))
    excerpt = FrozenExcerpt("summary", 2, 9, "literal", "hash")
    check = JudgementCitationCheck(
        "KJ1",
        CitationStatus.REVIEW_REQUIRED,
        (
            CitationCheck(
                "E2",
                "contradicting",
                CitationStatus.REVIEW_REQUIRED,
                "E2",
                "content",
                excerpt,
                (),
                ("Check attribution.",),
            ),
        ),
        (),
    )
    version = replace(
        version,
        body=body,
        evidence=evidence,
        assessment=assessment,
        citation_checks=ReportCitationChecks("old-citation-policy", (check,)),
    )

    def no_rescoring(*args, **kwargs):
        raise AssertionError("Claim inspection must not call scoring policy")

    monkeypatch.setattr("ase.domain.judgement_assessment.assess_judgement", no_rescoring)
    ledger = build_claim_ledger(version)
    claim = ledger.claims[0]
    assert claim.assessment is frozen and claim.citation_checks is check
    assert claim.citation_checks.citations[0].excerpt is excerpt
    assert claim.sources[1].relation == "contradicting"
    assert claim.sources[1].organisation is None
    assert ledger.recorded_gaps == ("Original source remains unknown.",)
    dimensions = {dimension.name: dimension.status for dimension in claim.dimensions}
    assert dimensions == {
        "evidence_support": "unsupported",
        "source_independence": "declared_only",
        "coverage": "unknown",
        "citation_validity": "review_required",
    }
    wire = ReportVersionOut.from_version(version).model_dump(mode="json")["claim_ledger"]
    assert wire["claims"][0]["assessment"]["explanation"] == ["Saved rule."]


def test_unknown_labels_and_empty_reports_are_not_silently_repaired() -> None:
    _, version = document_records()
    version = replace(version, body=ReportBody(key_judgements=(judgement("E999"),)))
    source = build_claim_ledger(version).claims[0].sources[0]
    assert source.label == "E999"
    assert source.evidence_id is None and source.content_hash is None
    assert build_claim_ledger(replace(version, body=ReportBody())).claims == ()
