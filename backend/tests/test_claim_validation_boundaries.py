"""Bounded locator inputs and cited URLs retain their rejection and acceptance paths."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ase.domain.claim_passage_validation import check_claim_passages, check_forecast_fields
from ase.domain.report_prose_validation import check_prose
from ase.domain.reports import parse_body
from report_helpers import GOOD_BODY
from test_claim_passage_validation import _sample


@pytest.mark.parametrize(
    "claim,citation_count,passage_count", [("", 1, 1), ("x", 21, 1), ("x", 1, 41)]
)
def test_untrusted_passage_checks_reject_unbounded_input(claim, citation_count, passage_count):
    passage, citation = _sample()
    with pytest.raises(ValueError, match="bounded input"):
        check_claim_passages(
            "C1",
            claim,
            (citation,) * citation_count,
            {str(index): passage for index in range(passage_count)},
            frozenset({"E1"}),
        )


def test_duplicate_passage_citations_are_rejected_independently():
    passage, citation = _sample()
    findings = check_claim_passages(
        "C1", passage.text, (citation, citation), {passage.id: passage}, frozenset({"E1"})
    )
    assert [finding.message for finding in findings] == ["Duplicate passage citation"]


@pytest.mark.parametrize(
    "kind,issued,reason",
    [
        ("other", datetime(2026, 9, 1, tzinfo=UTC), "kind"),
        ("forecast", datetime(2026, 9, 1), "timezone-aware"),
    ],
)
def test_invalid_forecast_identity_is_rejected(kind, issued, reason):
    with pytest.raises(ValueError, match=reason):
        check_forecast_fields(
            "F1",
            kind=kind,
            issued_at=issued,
            horizon_end=None,
            resolution_criterion=None,
            review_at=None,
        )


def test_exact_url_from_cited_evidence_is_allowed():
    body = parse_body(GOOD_BODY)
    label = next(iter(body.cited_labels()))
    body = replace(body, sourcing_statement="Source context: https://example.org/frozen.")
    findings = []
    check_prose(body, {label: "https://example.org/frozen"}, findings)
    assert not any(finding.rule == "url" for finding in findings)
