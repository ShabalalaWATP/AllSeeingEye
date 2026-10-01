"""Citation verdict anchors, currency and tallies, independent of storage."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ase.domain.citation_verdict_export import verdict_rows
from ase.domain.citation_verdicts import (
    CitationAnchor,
    CitationVerdict,
    CitationVerdictValue,
    cited_anchor,
    tally_verdicts,
)
from report_documents_helpers import document_records

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def _verdict(version, reviewer, verdict="supports", label="E1", minutes=0, **changes):
    values = {
        "id": uuid4(),
        "report_id": version.report_id,
        "report_version_id": version.id,
        "version_number": version.number,
        "anchor": CitationAnchor("KJ1", label, "supporting"),
        "verdict": CitationVerdictValue(verdict),
        "note": None,
        "owner_id": reviewer,
        "team_id": None,
        "reviewer_id": reviewer,
        "recorded_at": NOW + timedelta(minutes=minutes),
    }
    values.update(changes)
    return CitationVerdict(**values)


def test_anchor_requires_the_frozen_citation_and_relation() -> None:
    _, version = document_records()
    assert cited_anchor(version.body, "KJ1", "E1", "supporting") == CitationAnchor(
        "KJ1", "E1", "supporting"
    )
    for args in (("KJ1", "E3", "supporting"), ("KJ1", "E1", "contradicting"), ("KJ9", "E1", "x")):
        with pytest.raises(ValueError):
            cited_anchor(version.body, *args)
    with pytest.raises(ValueError):
        CitationAnchor("KJ1", "E1", "neutral")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        CitationAnchor(" ", "E1", "supporting")


def test_verdict_values_are_validated() -> None:
    _, version = document_records()
    reviewer = uuid4()
    for change in (
        {"note": "x" * 301},
        {"note": "  "},
        {"version_number": 0},
        {"recorded_at": datetime(2026, 10, 1)},
        {"reviewer_id": "someone"},
        {"id": "not-a-uuid"},
        {"verdict": "supports"},
        {"anchor": ("KJ1", "E1", "supporting")},
    ):
        values = {
            "id": uuid4(),
            "report_id": version.report_id,
            "report_version_id": version.id,
            "version_number": 1,
            "anchor": CitationAnchor("KJ1", "E1", "supporting"),
            "verdict": CitationVerdictValue.SUPPORTS,
            "note": None,
            "owner_id": reviewer,
            "team_id": None,
            "reviewer_id": reviewer,
            "recorded_at": NOW,
            **change,
        }
        with pytest.raises(ValueError):
            CitationVerdict(**values)


def test_tally_counts_each_reviewers_latest_verdict_per_citation() -> None:
    _, version = document_records()
    first, second = uuid4(), uuid4()
    rows = (
        _verdict(version, first, "cannot_tell"),
        _verdict(version, first, "supports", minutes=1),
        _verdict(version, second, "does_not_support", minutes=2),
        _verdict(version, second, "partly_supports", label="E2", minutes=3),
    )
    tally = tally_verdicts(rows)
    assert (tally.supports, tally.partly_supports, tally.does_not_support) == (1, 1, 1)
    assert (tally.cannot_tell, tally.current_verdicts, tally.superseded_verdicts) == (0, 3, 1)
    assert (tally.citations_with_verdicts, tally.reviewers) == (2, 2)


def test_export_rows_refuse_another_version() -> None:
    _, version = document_records()
    other = replace(version, id=uuid4())
    with pytest.raises(ValueError):
        verdict_rows(version, (_verdict(other, uuid4()),))
    row = verdict_rows(version, (_verdict(version, uuid4()),))[0]
    assert row["excerpt"] is None and row["citation_check_status"] is None
