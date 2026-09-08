"""Older metadata survives the real collector using explicit calendar-day selection."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.application.research.collection import ResearchCollector
from ase.domain.events import freeze_attributes
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_matches_time, evidence_time
from ase.domain.sec_filing_time import filing_source_date
from feeds_helpers import make_event
from research_records_helpers import CLOCK, COMPANY
from sec_filings_helpers import ARCHIVE, INDEX, SecTransport, columns, index


@pytest.mark.parametrize("older", [False, True])
async def test_older_filing_reaches_actual_collector_without_inventing_publication_time(
    monkeypatch: pytest.MonkeyPatch,
    older: bool,
) -> None:
    transport = SecTransport(monkeypatch)
    transport.responses[INDEX] = index(0 if older else 1)
    if not older:
        transport.responses[INDEX]["filings"]["recent"] = columns(filed="2025-06-01")
        transport.responses[INDEX]["filings"]["files"] = []
    transport.responses[f"https://data.sec.gov/submissions/{ARCHIVE}"] = columns(
        filed="2025-06-01",
    )
    query = replace(
        COMPANY, since=datetime(2025, 6, 1, tzinfo=UTC), until=datetime(2025, 6, 2, tzinfo=UTC)
    )
    try:
        result = await ResearchCollector([SecSubmissionsProvider(transport.http, CLOCK)]).collect(
            query
        )
        assert len(result.items) == result.attempts[0].result_count == 1
        assert result.items[0].published_at is None
        assert result.items[0].attributes["filing_date"] == "2025-06-01"
        assert "calendar days" in result.attempts[0].explanation
        assert result.items[0].source_dates == (filing_source_date("2025-06-01"),)
        assert len(transport.requests) == (2 if older else 1)
    finally:
        await transport.http.aclose()


@pytest.mark.parametrize(
    ("since", "until", "expected"),
    [
        ("2025-06-01T12:00:00+00:00", "2025-06-01T13:00:00+00:00", True),
        ("2025-05-31T00:00:00+00:00", "2025-06-01T00:00:00+00:00", False),
        ("2025-06-02T00:00:00+00:00", "2025-06-03T00:00:00+00:00", False),
    ],
    ids=["possible-part-day", "exclusive-upper-day", "outside"],
)
def test_day_policy_is_narrow_and_preserves_unknown_time_exclusion(
    since: str,
    until: str,
    expected: bool,
) -> None:
    event = replace(
        make_event("sec-day"),
        source_id="research-sec-submissions",
        published_at=None,
        source_dates=(filing_source_date("2025-06-01"),),
        attributes=freeze_attributes(
            {"record_kind": "filing_metadata", "date_precision": "day", "filing_date": "2025-06-01"}
        ),
    )
    start, end = datetime.fromisoformat(since), datetime.fromisoformat(until)
    assert evidence_time(event) is None
    assert evidence_matches_time(event, EvidenceTimeBasis.PUBLICATION, start, end) is expected
    assert not evidence_matches_time(
        replace(event, source_id="another-source"), EvidenceTimeBasis.PUBLICATION, start, end
    )
    assert not evidence_matches_time(event, EvidenceTimeBasis.RECORDED, start, end)


@pytest.mark.parametrize(
    "defect",
    [
        "absent",
        "duplicate",
        "role",
        "modification",
        "unspecified",
        "basis",
        "field",
        "raw",
        "status",
        "kind",
    ],
)
def test_unsuitable_typed_dates_never_fall_back_to_sec_attributes(defect):
    row = filing_source_date("2025-06-01")
    dates = (row,)
    if defect == "absent":
        dates = ()
    elif defect == "duplicate":
        dates = (row, row)
    elif defect in {"role", "modification", "unspecified"}:
        dates = (replace(row, role="occurrence" if defect == "role" else defect),)
    elif defect == "basis":
        dates = (replace(row, basis="operator"),)
    elif defect == "field":
        dates = (replace(row, field="summary"),)
    elif defect == "raw":
        dates = (replace(row, raw_text="2025-6-1"),)
    elif defect == "status":
        dates = (replace(row, status="invalid", precision="unknown", day_start=None, day_end=None),)
    event = replace(
        make_event("sec"),
        source_id="research-sec-submissions",
        published_at=None,
        source_dates=dates,
        attributes=freeze_attributes(
            {
                "record_kind": "sec_filing_content" if defect == "kind" else "filing_metadata",
                "filing_date": "2025-06-01",
                "date_precision": "day",
            }
        ),
    )
    assert not evidence_matches_time(
        event,
        EvidenceTimeBasis.PUBLICATION,
        datetime(2025, 6, 1, tzinfo=UTC),
        datetime(2025, 6, 2, tzinfo=UTC),
    )


def test_typed_filing_day_open_and_offset_bounds_are_calendar_labels():
    event = replace(
        make_event("sec"),
        source_id="research-sec-submissions",
        published_at=None,
        source_dates=(filing_source_date("2025-06-01"),),
        attributes=freeze_attributes({"record_kind": "filing_metadata"}),
    )
    assert evidence_matches_time(event, EvidenceTimeBasis.PUBLICATION, None, None)
    assert evidence_matches_time(
        event,
        EvidenceTimeBasis.PUBLICATION,
        datetime.fromisoformat("2025-06-01T23:00:00-10:00"),
        None,
    )
    assert not evidence_matches_time(
        event,
        EvidenceTimeBasis.PUBLICATION,
        None,
        datetime.fromisoformat("2025-06-01T00:00:00+14:00"),
    )
