"""Canonical SEC dates survive unchanged; one malformed row cannot poison a page."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.adapters.research_records.sec_history import archives, page
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, COMPANY
from sec_filings_helpers import ARCHIVE, CIK, INDEX, SecTransport, columns, index


@pytest.mark.parametrize(
    "invalid",
    [
        "20240229",
        "2024-W09-4",
        "2024-2-29",
        "2024-02-9",
        " 2024-02-29",
        "2024-02-29 ",
        "２０２４-02-29",  # noqa: RUF001 - deliberately reject non-ASCII provider digits.
        "2024-02-30",
        "2023-02-29",
    ],
    ids=[
        "compact",
        "week",
        "month-padding",
        "day-padding",
        "leading-space",
        "trailing-space",
        "unicode-digits",
        "invalid-day",
        "non-leap",
    ],
)
@pytest.mark.parametrize("path", ["selected-recent", "selected-older", "automatic-older"])
async def test_invalid_date_is_skipped_without_losing_valid_filings(
    invalid: str,
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SecTransport(monkeypatch)
    data = index(0)
    data["filings"]["files"][0].update(filingFrom="2024-01-01", filingTo="2024-12-31")
    body = columns(3)
    body["filingDate"] = ["2024-02-29", invalid, "2024-03-01"]
    if path == "selected-recent":
        data["filings"]["recent"] = body
    transport.responses[INDEX] = data
    transport.responses[f"https://data.sec.gov/submissions/{ARCHIVE}"] = body
    since, until = datetime(2024, 1, 1, tzinfo=UTC), datetime(2025, 1, 1, tzinfo=UTC)
    try:
        if path == "automatic-older":
            result = await SecSubmissionsProvider(transport.http, CLOCK).collect(
                replace(COMPANY, since=since, until=until)
            )
            assert result.attempts[0].status is CollectionStatus.COMPLETED
            assert len(result.items) == 2
            assert {event.attributes["filing_date"] for event in result.items} == {
                "2024-02-29",
                "2024-03-01",
            }
            assert all(event.published_at is None for event in result.items)
            assert all(
                event.source_dates[0].raw_text == event.attributes["filing_date"]
                for event in result.items
            )
        else:
            result = await page(
                transport.client,
                CIK,
                since.date(),
                until.date(),
                0 if path == "selected-recent" else 1,
                0,
            )
            assert len(result.items) == 2
            assert {filing.filing_date.isoformat() for filing in result.items} == {
                "2024-02-29",
                "2024-03-01",
            }
        assert len(transport.requests) == (1 if path == "selected-recent" else 2)
    finally:
        await transport.http.aclose()


@pytest.mark.parametrize("invalid", ["20250101", "2025-W01-3", "2025-1-01", "2025-02-30"])
def test_noncanonical_archive_range_is_skipped_without_losing_valid_page(invalid: str) -> None:
    data = index()
    data["filings"]["files"].append(
        {
            "name": f"CIK{CIK}-submissions-002.json",
            "filingFrom": invalid,
            "filingTo": "2025-12-31",
        }
    )
    assert archives(data, CIK, date(2025, 1, 1), date(2025, 12, 31)) == ([ARCHIVE], False)
