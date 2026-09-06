"""SEC candidate ambiguity, accession integrity and bounded collection receipts."""

from dataclasses import replace
from typing import Any

import pytest

from ase.adapters.research_records import (
    CompaniesHouseUnavailableProvider,
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.company import DIRECTORY_URL, cik
from ase.domain.events import Credibility
from ase.domain.research import CollectionStatus, ResearchFocus
from research_records_helpers import CLOCK, COMPANY, RecordService, submissions


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1234, "0000001234"),
        ("cik: 1234", "0000001234"),
        ("0", None),
        (True, None),
        (None, None),
        ("Example", None),
        ("12345678901", None),
        ("12/34", None),
    ],
)
def test_cik_requires_explicit_nonzero_identifier(value: Any, expected: str | None) -> None:
    assert cik(value) == expected


async def test_sec_one_request_stable_public_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(monkeypatch, submissions(25))
    provider = SecSubmissionsProvider(service.http, CLOCK)
    batch = await provider.collect(COMPANY)
    assert len(batch.items) == batch.attempts[0].result_count == 20
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    request = service.requests[0]
    assert len(service.requests) == len(service.guarded) == 1
    assert str(request.url) == "https://data.sec.gov/submissions/CIK0000001234.json"
    assert COMPANY.question not in str(request.url)
    assert not request.headers.get("authorization")
    first = batch.items[0]
    assert first.url == (
        "https://www.sec.gov/Archives/edgar/data/1234/000000123426000000/"
        "0000001234-26-000000-index.html"
    )
    assert first.credibility is Credibility.CANNOT_BE_JUDGED
    assert first.attributes["date_precision"] == "day"
    assert first.published_at.date() == COMPANY.since.date()
    assert first.observed_at == CLOCK.now()
    assert "not verified" in (first.summary or "")
    again = await provider.collect(COMPANY)
    assert again.items == batch.items
    assert len(service.requests) == 2
    await service.http.aclose()


async def test_sec_skips_bad_duplicate_and_outside_window_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = submissions(8)
    recent = data["filings"]["recent"]
    recent["accessionNumber"][0] = "https://127.0.0.1/secret"
    recent["accessionNumber"][1] = None
    recent["accessionNumber"][2] = recent["accessionNumber"][3]
    recent["filingDate"][4] = "invalid"
    recent["filingDate"][5] = "2020-01-01"
    recent["filingDate"][6] = None
    recent["form"][7] = {}
    service = RecordService(monkeypatch, data)
    batch = await SecSubmissionsProvider(service.http, CLOCK).collect(COMPANY)
    assert len(batch.items) == 1
    assert batch.items[0].attributes["accession"] == recent["accessionNumber"][3]
    assert len(service.requests) == 1
    await service.http.aclose()


@pytest.mark.parametrize("damage", ["identity", "name", "filings", "recent", "column", "length"])
async def test_sec_rejects_untrusted_identity_or_shapes(
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    data = submissions()
    if damage == "identity":
        data["cik"] = 9999
    elif damage == "name":
        data["name"] = None
    elif damage == "filings":
        data["filings"] = []
    elif damage == "recent":
        data["filings"]["recent"] = []
    elif damage == "column":
        data["filings"]["recent"]["form"] = None
    else:
        data["filings"]["recent"]["form"] = []
    service = RecordService(monkeypatch, data)
    batch = await SecSubmissionsProvider(service.http, CLOCK).collect(COMPANY)
    assert batch.items == ()
    assert batch.attempts[0].status is CollectionStatus.FAILED
    await service.http.aclose()


async def test_no_matching_filing_is_an_explicit_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, submissions(0))
    batch = await SecSubmissionsProvider(service.http, CLOCK).collect(COMPANY)
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    await service.http.aclose()


async def test_company_providers_do_not_silently_resolve_or_fetch_wrong_focus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch)
    filings = SecSubmissionsProvider(service.http, CLOCK)
    directory = SecCompanyDirectoryProvider(service.http, CLOCK)
    for provider, query in [
        (filings, replace(COMPANY, subject="Example")),
        (filings, replace(COMPANY, focus=ResearchFocus.GENERAL)),
        (directory, COMPANY),
        (directory, replace(COMPANY, subject=" ")),
    ]:
        assert not provider.supports(query)
        assert (await provider.collect(query)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert service.requests == []
    await service.http.aclose()


async def test_directory_ambiguity_bounded_candidates_no_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = {
        str(i): {"cik_str": i, "title": f"Example Company {i}", "ticker": f"E{i}"}
        for i in range(1, 15)
    }
    data["exact"] = {"cik_str": 20, "title": "Example", "ticker": "EX"}
    data["duplicate"] = data["exact"]
    data["invalid"] = []
    data["bad_cik"] = {"cik_str": 0, "title": "Example", "ticker": "EX"}
    service = RecordService(monkeypatch, data)
    query = replace(COMPANY, subject="example")
    batch = await SecCompanyDirectoryProvider(service.http, CLOCK).collect(query)
    assert len(batch.items) == 8
    assert len({item.id for item in batch.items}) == 8
    assert batch.items[0].attributes["cik"] == "0000000020"
    assert all(item.attributes["identity_match"] == "candidate_only" for item in batch.items)
    assert all(item.published_at == CLOCK.now() for item in batch.items)
    assert len(service.requests) == 1
    assert str(service.requests[0].url) == DIRECTORY_URL
    assert query.subject not in str(service.requests[0].url)
    await service.http.aclose()


async def test_directory_short_ticker_requires_exact_match(monkeypatch: pytest.MonkeyPatch) -> None:
    data = {"0": {"cik_str": 1, "title": "EXAMPLE", "ticker": "LONG"}}
    service = RecordService(monkeypatch, data)
    provider = SecCompanyDirectoryProvider(service.http, CLOCK)
    batch = await provider.collect(replace(COMPANY, subject="ex"))
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    batch = await provider.collect(replace(COMPANY, subject="long"))
    assert len(batch.items) == 1
    await service.http.aclose()


async def test_companies_house_reports_missing_safe_credential_transport() -> None:
    provider = CompaniesHouseUnavailableProvider()
    batch = await provider.collect(replace(COMPANY, country_iso="GB"))
    assert batch.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "no request or credential was sent" in batch.attempts[0].explanation
    assert (await provider.collect(COMPANY)).attempts[0].status is CollectionStatus.UNSUPPORTED
