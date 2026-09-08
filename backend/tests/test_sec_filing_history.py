"""Bounded older SEC pages and exact document selection without web crawling."""

from dataclasses import replace
from datetime import UTC, date, datetime

import httpx
import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.adapters.research_records.sec_history import archives, page, rows
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, COMPANY
from sec_filings_helpers import ARCHIVE, CIK, INDEX, SecTransport, columns, index


async def test_recent_and_declared_older_pages_select_exact_primary_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SecTransport(monkeypatch)
    transport.responses[INDEX] = index(25)
    older = f"https://data.sec.gov/submissions/{ARCHIVE}"
    transport.responses[older] = columns(1, filed="2025-06-01")
    try:
        first = await page(transport.client, CIK, date(2025, 1, 1), date(2026, 9, 1), 0, 0)
        assert len(first.items) == 20 and first.next_offset == 20
        second = await page(transport.client, CIK, date(2025, 1, 1), date(2026, 9, 1), 0, 20)
        assert len(second.items) == 5 and second.next_offset is None
        historical = await page(transport.client, CIK, date(2025, 1, 1), date(2026, 9, 1), 1, 0)
        assert historical.items[0].filing_date == date(2025, 6, 1)
        assert historical.items[0].accession.startswith("0000999999")
        assert historical.items[0].cik == CIK  # Filing-agent prefix need not equal issuer CIK.
        assert [str(request.url) for request in transport.requests] == [INDEX] * 3 + [older]
        assert all(
            b - a >= 0.24 for a, b in zip(transport.times, transport.times[1:], strict=False)
        )
    finally:
        await transport.http.aclose()


async def test_automatic_collection_fetches_at_most_three_matching_history_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SecTransport(monkeypatch)
    data = index(0)
    data["filings"]["files"] = []
    for number in range(5):
        name = f"CIK{CIK}-submissions-{number:03d}.json"
        data["filings"]["files"].append(
            {
                "name": name,
                "filingFrom": "2025-01-01",
                "filingTo": "2025-12-31",
            }
        )
        body = columns(1, filed="2025-06-01")
        body["accessionNumber"] = [f"0000999999-25-{number:06d}"]
        transport.responses[f"https://data.sec.gov/submissions/{name}"] = body
    transport.responses[INDEX] = data
    try:
        result = await SecSubmissionsProvider(
            transport.http, CLOCK, client=transport.client
        ).collect(replace(COMPANY, since=datetime(2025, 1, 1, tzinfo=UTC)))
        assert len(transport.requests) == 4 and len(result.items) == 3
        assert result.attempts[0].status is CollectionStatus.COMPLETED
        assert "3 of 5" in result.attempts[0].explanation
        assert all(item.attributes["record_kind"] != "sec_filing_content" for item in result.items)
    finally:
        await transport.http.aclose()


def test_manifest_scope_and_selection_rows_are_bounded_and_validated() -> None:
    data = index()
    data["filings"]["files"] += [
        {"name": "https://private/secret", "filingFrom": "2025-01-01", "filingTo": "2025-12-31"},
        {
            "name": "CIK0000000001-submissions-001.json",
            "filingFrom": "2025-01-01",
            "filingTo": "2025-12-31",
        },
    ]
    assert archives(data, CIK, date(2025, 1, 1), date(2025, 12, 31)) == ([ARCHIVE], False)
    assert archives(data, CIK, date(2026, 1, 1), date(2026, 9, 1)) == ([], False)
    with pytest.raises(ValueError, match="oversized"):
        rows(columns(10001), CIK, "Issuer", date(2020, 1, 1), date(2026, 9, 1))
    broken = columns()
    broken["form"] = []
    with pytest.raises(ValueError, match="Misaligned"):
        rows(broken, CIK, "Issuer", date(2020, 1, 1), date(2026, 9, 1))


async def test_configuration_and_resource_allowlist_fail_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SecTransport(monkeypatch)
    try:
        for url in (
            "https://example.com/a",
            INDEX + "?url=private",
            INDEX.replace("https", "http"),
        ):
            with pytest.raises(FeedFetchError):
                await transport.client.get_bytes(url)
        transport.http._client.headers["User-Agent"] = "ASE set-ASE_FEEDS_CONTACT@example.invalid"
        result = await SecSubmissionsProvider(transport.http, CLOCK).collect(COMPANY)
        assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
        assert "ASE_FEEDS_CONTACT" in result.attempts[0].explanation
        assert transport.requests == []
    finally:
        await transport.http.aclose()


async def test_redirect_is_not_followed_and_failed_history_is_explicit_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = SecTransport(monkeypatch)
    transport.responses[f"https://data.sec.gov/submissions/{ARCHIVE}"] = httpx.Response(
        302,
        headers={"Location": "https://private.example/secret"},
    )
    try:
        result = await SecSubmissionsProvider(transport.http, CLOCK).collect(
            replace(COMPANY, since=datetime(2025, 1, 1, tzinfo=UTC))
        )
        assert result.attempts[0].status is CollectionStatus.FAILED
        assert len(result.items) == 1 and len(transport.requests) == 2
        assert "partial" in result.attempts[0].explanation
    finally:
        await transport.http.aclose()
