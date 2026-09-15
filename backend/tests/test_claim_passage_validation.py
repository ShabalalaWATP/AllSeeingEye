"""Frozen-passage locator integrity and conservative literal review signals."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.domain.claim_passage_validation import (
    ClaimPassageCitation,
    FrozenClaimPassage,
    check_claim_passages,
    check_forecast_fields,
)
from ase.domain.reports import parse_body
from ase.domain.validation import validate_body
from ase.domain.validation_types import Severity
from report_helpers import GOOD_BODY


def _sample(
    text: str = "The agency recorded 12 km on 2 May 2026 and reported no disruption.",
    *,
    language: str | None = "en",
) -> tuple[FrozenClaimPassage, ClaimPassageCitation]:
    passage = FrozenClaimPassage(
        "passage-1",
        "version-1",
        "E1",
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        text,
        language,
    )
    citation = ClaimPassageCitation("passage-1", "version-1", "E1", 0, len(text), text)
    return passage, citation


def test_exact_frozen_passage_and_attributed_statistics_do_not_claim_truth() -> None:
    passage, citation = _sample(
        "The statistical agency reported inflation of 3.2 percent across 10 kilometres."
    )
    findings = check_claim_passages(
        "C1",
        "The statistical agency reported inflation of 3.2 percent across 10 km.",
        (citation,),
        {passage.id: passage},
        frozenset({"E1"}),
    )
    assert findings == ()


def test_fabricated_or_misaligned_passage_fails_locator_integrity() -> None:
    passage, citation = _sample()
    for bad in (
        replace(citation, passage_id="invented"),
        replace(citation, document_version_id="different"),
        replace(citation, evidence_label="E2"),
        replace(citation, excerpt="invented quote"),
        replace(citation, start=True),
    ):
        findings = check_claim_passages(
            "C1",
            "The agency reported 12 km.",
            (bad,),
            {passage.id: passage},
            frozenset({"E1", "E2"}),
        )
        assert any(f.rule == "citation" and f.severity is Severity.ERROR for f in findings)
    corrupt = replace(passage, text_sha256="0" * 64)
    findings = check_claim_passages(
        "C1",
        "The agency reported 12 km.",
        (citation,),
        {passage.id: corrupt},
        frozenset({"E1"}),
    )
    assert any(f.rule == "passage_integrity" for f in findings)
    renamed = replace(passage, id="different")
    findings = check_claim_passages(
        "C1",
        "The agency reported 12 km.",
        (citation,),
        {citation.passage_id: renamed},
        frozenset({"E1"}),
    )
    assert any(f.rule == "citation" for f in findings)
    assert (
        check_claim_passages(
            "C1",
            "The agency reported 12 km.",
            (),
            {passage.id: passage},
            frozenset({"E1"}),
        )[0].severity
        is Severity.ERROR
    )


def test_number_date_unit_and_negation_are_review_cues_only() -> None:
    passage, citation = _sample()
    findings = check_claim_passages(
        "C1",
        "The agency recorded 12 miles and 13 incidents on 3 May 2026 with disruption.",
        (citation,),
        {passage.id: passage},
        frozenset({"E1"}),
    )
    messages = " ".join(f.message for f in findings)
    assert all(
        signal in messages
        for signal in ("number_mismatch", "date_mismatch", "negation_mismatch", "unit_mismatch")
    )
    assert all(f.severity is Severity.WARNING for f in findings)


def test_name_or_attribution_cue_requires_review_not_factual_rejection() -> None:
    passage, citation = _sample("The Ministry of Health reported 14 cases in Delhi.")
    findings = check_claim_passages(
        "C1",
        "The Finance Ministry reported 14 cases in Delhi.",
        (citation,),
        {passage.id: passage},
        frozenset({"E1"}),
    )
    assert any("name_mismatch" in finding.message for finding in findings)
    assert all(f.severity is Severity.WARNING for f in findings)


def test_untranslated_original_skips_english_literal_comparison() -> None:
    passage, citation = _sample(language="uk")
    findings = check_claim_passages(
        "C1",
        "It reports 55 miles on 3 May 2026 with disruption.",
        (citation,),
        {passage.id: passage},
        frozenset({"E1"}),
    )
    assert {f.rule for f in findings} == {"passage_language"}


def test_report_validator_checks_supplied_exact_passage_links() -> None:
    passage, citation = _sample()
    body = parse_body(GOOD_BODY)
    result = validate_body(
        body,
        frozenset({"E1", "E2", "E3"}),
        {},
        original_passages={passage.id: passage},
        passage_citations={"KJ1": (replace(citation, excerpt="fabricated"),)},
    )
    assert any(f.rule == "citation" and f.location == "KJ1" for f in result.errors)
    with pytest.raises(ValueError, match="supplied together"):
        validate_body(body, frozenset({"E1"}), {}, original_passages={passage.id: passage})


def test_forecast_requires_dated_horizon_observable_criterion_and_review() -> None:
    issued = datetime(2026, 9, 14, tzinfo=UTC)
    bad = check_forecast_fields(
        "F1",
        kind="forecast",
        issued_at=issued,
        horizon_end=None,
        resolution_criterion="Because.",
        review_at=None,
    )
    assert len(bad) == 3 and all(f.severity is Severity.ERROR for f in bad)
    valid = check_forecast_fields(
        "F1",
        kind="forecast",
        issued_at=issued,
        horizon_end=issued + timedelta(days=7),
        resolution_criterion="A published ceasefire agreement remains in force for seven days.",
        review_at=issued + timedelta(days=8),
    )
    assert valid == ()
    assert (
        check_forecast_fields(
            "O1",
            kind="observation",
            issued_at=issued,
            horizon_end=None,
            resolution_criterion=None,
            review_at=None,
        )
        == ()
    )
