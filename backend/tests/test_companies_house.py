"""Companies House snapshots do not leak credentials or automatically resolve identities."""

import base64
from dataclasses import replace
from datetime import timedelta
from typing import Any

import httpx
import pytest

from ase.adapters.research_records.companies_house import (
    ORIGIN,
    CompaniesHouseProvider,
    company_number,
)
from ase.domain.research import CollectionStatus, ResearchFocus
from research_records_helpers import CLOCK, QUERY, RecordService

KEY = "synthetic-api-fixture"
COMPANY = replace(QUERY, focus=ResearchFocus.COMPANY, subject="GB:1234567")


def profile(number: str = "01234567", name: str = "SYNTHETIC COMPANY LIMITED") -> dict[str, Any]:
    return {
        "company_number": number,
        "company_name": name,
        "company_status": "active",
        "type": "ltd",
        "date_of_creation": "1990-01-01",
    }


async def test_profile_request_uses_basic_key_username_and_preserves_current_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, profile())
    provider = CompaniesHouseProvider(service.http, CLOCK, KEY)
    batch = await provider.collect(COMPANY)
    assert len(service.requests) == len(service.guarded) == len(batch.items) == 1
    request = service.requests[0]
    assert str(request.url) == f"{ORIGIN}/company/01234567"
    assert (
        request.headers["authorization"] == "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()
    )
    event = batch.items[0]
    assert event.grade == "F6"
    assert event.published_at == event.observed_at == CLOCK.now()
    assert event.attributes["reported_date_of_creation"] == "1990-01-01"
    assert event.attributes["identity_match"] == "requested_company_number"
    assert event.country_iso is None and event.point is None
    assert "not a historical view" in batch.attempts[0].explanation
    assert KEY not in repr(batch) and KEY not in repr(provider._credential)
    await service.http.aclose()


async def test_name_search_returns_distinct_candidates_without_follow_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"company_number": f"{index:08}", "title": "SAME NAME LTD", "company_status": "active"}
        for index in range(30)
    ]
    service = RecordService(monkeypatch, {"items": rows})
    query = replace(COMPANY, subject="Same Name & Company")
    batch = await CompaniesHouseProvider(service.http, CLOCK, KEY).collect(query)
    assert len(service.requests) == 1 and len(batch.items) == 20
    assert service.requests[0].url.params["q"] == query.subject
    assert service.requests[0].url.params["items_per_page"] == "20"
    assert all(event.attributes["identity_match"] == "candidate_only" for event in batch.items)
    assert len({event.id for event in batch.items}) == 20
    assert query.question not in str(service.requests[0].url)
    await service.http.aclose()


async def test_missing_key_and_unsupported_subjects_do_not_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, profile())
    provider = CompaniesHouseProvider(service.http, CLOCK)
    assert (await provider.collect(COMPANY)).attempts[0].status is CollectionStatus.UNAVAILABLE
    for query in (
        QUERY,
        replace(COMPANY, subject=None),
        replace(COMPANY, subject="CIK 1234"),
        replace(COMPANY, subject="GB:../../evil"),
        replace(COMPANY, country_iso="US"),
    ):
        assert (await provider.collect(query)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not service.requests
    await service.http.aclose()


@pytest.mark.parametrize(
    "payload",
    [[], {"company_number": "99999999", "company_name": "secret"}, {"company_number": "01234567"}],
)
async def test_invalid_profile_shape_or_identity_is_rejected(
    monkeypatch: pytest.MonkeyPatch, payload: Any
) -> None:
    service = RecordService(monkeypatch, payload)
    result = await CompaniesHouseProvider(service.http, CLOCK, KEY).collect(COMPANY)
    assert result.attempts[0].status is CollectionStatus.FAILED and not result.items
    assert "secret" not in repr(result)
    await service.http.aclose()


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 302])
async def test_upstream_errors_are_safe_and_never_retried(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    response = httpx.Response(
        status, text=f"secret body {KEY}", headers={"location": "https://other.example/secret"}
    )
    service = RecordService(monkeypatch, response=response)
    result = await CompaniesHouseProvider(service.http, CLOCK, KEY).collect(COMPANY)
    assert len(service.requests) == 1
    assert result.attempts[0].status is CollectionStatus.FAILED
    assert KEY not in repr(result) and "secret" not in repr(result)
    await service.http.aclose()


async def test_local_rate_allowance_counts_calls_and_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, profile())
    provider = CompaniesHouseProvider(service.http, CLOCK, KEY)
    provider._requests.extend([CLOCK.now()] * 600)
    exhausted = await provider.collect(COMPANY)
    assert (
        exhausted.attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED and not service.requests
    )
    provider._requests.clear()
    provider._requests.append(CLOCK.now() - timedelta(minutes=5))
    assert (await provider.collect(COMPANY)).attempts[0].status is CollectionStatus.COMPLETED
    assert len(provider._requests) == 1
    await service.http.aclose()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("123", "00000123"),
        ("sc123456", "SC123456"),
        ("R1234567", "R1234567"),
        ("IP12345R", "IP12345R"),
        (True, None),
        ("../../host", None),
        ("Some Name", None),
    ],
)
def test_company_number_is_bounded_and_canonical(value: Any, expected: str | None) -> None:
    assert company_number(value) == expected


async def test_search_skips_invalid_duplicate_rows_and_reports_empty_or_failed_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = replace(COMPANY, subject="Synthetic company")
    row = {"company_number": "01234567", "title": "SYNTHETIC LTD"}
    service = RecordService(monkeypatch, {"items": [None, {}, row, row]})
    result = await CompaniesHouseProvider(service.http, CLOCK, KEY).collect(query)
    assert len(result.items) == 1
    await service.http.aclose()
    for data, status in (({"items": []}, CollectionStatus.EMPTY), ({}, CollectionStatus.FAILED)):
        service = RecordService(monkeypatch, data)
        result = await CompaniesHouseProvider(service.http, CLOCK, KEY).collect(query)
        assert result.attempts[0].status is status
        await service.http.aclose()


async def test_prefix_and_timeout_handling_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(monkeypatch, profile())
    provider = CompaniesHouseProvider(service.http, CLOCK, KEY)
    result = await provider.collect(replace(COMPANY, subject="companies-house:01234567"))
    assert result.attempts[0].status is CollectionStatus.COMPLETED

    async def timeout(*args: object, **kwargs: object) -> None:
        raise TimeoutError("secret request")

    monkeypatch.setattr(service.http, "get_json", timeout)
    result = await provider.collect(COMPANY)
    assert result.attempts[0].status is CollectionStatus.TIMED_OUT
    assert "secret" not in repr(result)
    await service.http.aclose()


@pytest.mark.parametrize(
    "key",
    ["x:y", "space key", "newline\nkey", "x" * 513],
    ids=["colon", "space", "newline", "size"],
)
async def test_invalid_key_configuration_does_not_echo_key(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
) -> None:
    service = RecordService(monkeypatch)
    with pytest.raises(ValueError, match="configuration") as error:
        CompaniesHouseProvider(service.http, CLOCK, key)
    assert key not in str(error.value)
    await service.http.aclose()
