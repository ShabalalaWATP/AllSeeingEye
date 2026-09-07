"""Exact registry identifiers, dated assertions and a shared keyed request budget."""

import json
from dataclasses import replace
from typing import Any

import httpx
import pytest

from ase.adapters.research_records.companies_house_client import CompaniesHouseClient
from ase.adapters.research_records.companies_house_people import (
    CompaniesHouseOfficersProvider,
    CompaniesHousePscProvider,
)
from ase.adapters.research_records.gleif import GleifParentProvider, GleifProfileProvider
from ase.domain.research import CollectionStatus, ResearchFocus
from research_records_helpers import CLOCK, QUERY, RecordService

LEI = "5493001KJTIIGC8Y1R12"
PARENT = "549300B56MD0ZC402L06"
COMPANY = replace(QUERY, focus=ResearchFocus.COMPANY, subject="GB:01234567")
ENTITY = replace(QUERY, focus=ResearchFocus.COMPANY, subject=f"LEI:{LEI}")


def gleif_profile() -> dict[str, Any]:
    return {
        "data": {
            "type": "lei-records",
            "id": LEI,
            "attributes": {
                "lei": LEI,
                "entity": {
                    "legalName": {"name": "شرکت نمونه", "language": "fa"},
                    "status": "ACTIVE",
                    "registeredAs": "123",
                    "jurisdiction": "GB",
                },
                "registration": {"status": "ISSUED", "lastUpdateDate": "2020-01-02T00:00:00Z"},
            },
            "links": {"self": "http://127.0.0.1/never-follow"},
        }
    }


def parent_record(kind: str = "direct") -> dict[str, Any]:
    return {
        "data": {
            "type": "relationship-records",
            "attributes": {
                "validFrom": "2020-01-02",
                "validTo": None,
                "relationship": {
                    "startNode": {"type": "LEI", "id": LEI},
                    "endNode": {"type": "LEI", "id": PARENT},
                    "type": "IS_DIRECTLY_CONSOLIDATED_BY"
                    if kind == "direct"
                    else "IS_ULTIMATELY_CONSOLIDATED_BY",
                    "status": "INACTIVE",
                    "periods": [
                        {
                            "type": "RELATIONSHIP_PERIOD",
                            "startDate": "2010-01-01",
                            "endDate": "2020-01-01",
                        }
                    ],
                },
                "registration": {
                    "lastUpdateDate": "2020-01-02",
                    "corroborationLevel": "ENTITY_SUPPLIED_ONLY",
                    "corroborationReference": "Reported filing 123",
                },
            },
        }
    }


def people(endpoint: str, count: int = 1) -> dict[str, Any]:
    return {
        "links": {"self": f"/company/01234567/{endpoint}"},
        "items": [
            {
                "name": f"Example Person {index}",
                "officer_role": "director",
                "appointed_on": "1990-01-01",
                "resigned_on": "2000-01-01",
                "notified_on": "2017-01-01",
                "ceased_on": "2019-01-01",
                "kind": "individual-person-with-significant-control",
                "natures_of_control": ["ownership-of-shares-25-to-50-percent"],
                "address": {"address_line_1": "Private-looking address must not be copied"},
                "links": {"self": f"/company/01234567/appointments/id{index}"},
            }
            for index in range(count)
        ],
    }


async def test_gleif_profile_one_exact_request_no_follow_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, gleif_profile())
    batch = await GleifProfileProvider(service.http, CLOCK).collect(ENTITY)
    await service.http.aclose()
    assert len(service.requests) == 1
    assert service.requests[0].url.path == f"/api/v1/lei-records/{LEI}"
    assert len(batch.items) == 1 and batch.items[0].grade == "F6"
    assert batch.items[0].attributes["legal_name"] == "شرکت نمونه"
    assert batch.items[0].attributes["reported_last_update"] == "2020-01-02T00:00:00Z"
    assert batch.items[0].published_at == CLOCK.now()
    assert "not a historical" in batch.attempts[0].explanation


@pytest.mark.parametrize("kind", ["direct", "ultimate"])
async def test_parent_relationship_retains_reported_dates_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
    kind: Any,
) -> None:
    service = RecordService(monkeypatch, parent_record(kind))
    batch = await GleifParentProvider(service.http, CLOCK, kind).collect(ENTITY)
    await service.http.aclose()
    assert len(service.requests) == 1 and len(batch.items) == 1
    item = batch.items[0]
    assert item.attributes["parent_lei"] == PARENT
    assert item.attributes["reported_relationship_status"] == "INACTIVE"
    assert item.attributes["reported_corroboration_reference"] == "Reported filing 123"
    assert json.loads(str(item.attributes["reported_periods"]))[0]["endDate"] == "2020-01-01"
    assert item.published_at == CLOCK.now() and item.grade == "F6"
    assert "not independent verification" in item.summary


async def test_parent_period_omissions_count_all_unretained_entries(monkeypatch):
    payload = parent_record()
    relationship = payload["data"]["attributes"]["relationship"]
    relationship["periods"] = [None, *relationship["periods"] * 25]
    service = RecordService(monkeypatch, payload)
    batch = await GleifParentProvider(service.http, CLOCK).collect(ENTITY)
    await service.http.aclose()
    attributes = batch.items[0].attributes
    retained = json.loads(str(attributes["reported_periods"]))
    assert len(retained) + attributes["reported_periods_omitted"] == 26


async def test_parent_mismatched_child_or_type_does_not_create_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for bad in ("child", "type", "parent"):
        payload = parent_record()
        relationship = payload["data"]["attributes"]["relationship"]
        if bad == "child":
            relationship["startNode"]["id"] = PARENT
        elif bad == "parent":
            relationship["endNode"]["id"] = "http://127.0.0.1"
        else:
            relationship["type"] = "IS_ULTIMATELY_CONSOLIDATED_BY"
        service = RecordService(monkeypatch, payload)
        batch = await GleifParentProvider(service.http, CLOCK).collect(ENTITY)
        await service.http.aclose()
        assert not batch.items and batch.attempts[0].status is CollectionStatus.FAILED


@pytest.mark.parametrize(
    "subject", ["Example Company", "GB:01234567", "https://api.gleif.org/record", "LEI:../../x"]
)
async def test_gleif_requires_exact_identifier_without_requests(
    monkeypatch: pytest.MonkeyPatch, subject: str
) -> None:
    service = RecordService(monkeypatch, {})
    batch = await GleifProfileProvider(service.http, CLOCK).collect(
        replace(ENTITY, subject=subject)
    )
    await service.http.aclose()
    assert not service.requests and batch.attempts[0].status is CollectionStatus.UNSUPPORTED


@pytest.mark.parametrize(
    "provider_type", [CompaniesHouseOfficersProvider, CompaniesHousePscProvider]
)
async def test_uk_relationships_are_bounded_snapshot_context(
    monkeypatch: pytest.MonkeyPatch, provider_type: Any
) -> None:
    service = RecordService(monkeypatch, people(provider_type.endpoint, 25))
    client = CompaniesHouseClient(service.http, CLOCK, "synthetic-key")
    batch = await provider_type(client, CLOCK).collect(COMPANY)
    await service.http.aclose()
    assert len(service.requests) == 1 and len(batch.items) == 20
    assert service.requests[0].url.params["items_per_page"] == "20"
    assert all(item.grade == "F6" and item.published_at == CLOCK.now() for item in batch.items)
    assert "Private-looking" not in repr(batch)
    assert "not a historical" in batch.attempts[0].explanation
    assert (
        "1990-01-01" in str(batch.items[0].attributes["reported_dates"])
        if provider_type.endpoint == "officers"
        else "2017-01-01" in str(batch.items[0].attributes["reported_dates"])
    )


async def test_uk_edges_require_explicit_registry_prefix_and_bound_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, people("officers"))
    provider = CompaniesHouseOfficersProvider(
        CompaniesHouseClient(service.http, CLOCK, "fake"), CLOCK
    )
    for subject in ("1234567", "Example Company", "CIK:1234", "GB:../x"):
        assert (await provider.collect(replace(COMPANY, subject=subject))).attempts[
            0
        ].status is CollectionStatus.UNSUPPORTED
    assert not service.requests
    await service.http.aclose()
    wrong = people("officers")
    wrong["links"]["self"] = "/company/87654321/officers"
    service = RecordService(monkeypatch, wrong)
    batch = await CompaniesHouseOfficersProvider(
        CompaniesHouseClient(service.http, CLOCK, "fake"), CLOCK
    ).collect(COMPANY)
    await service.http.aclose()
    assert batch.attempts[0].status is CollectionStatus.FAILED and not batch.items


async def test_uk_task_budget_shared_and_missing_key_makes_no_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, people("officers"))
    unavailable = CompaniesHousePscProvider(CompaniesHouseClient(service.http, CLOCK), CLOCK)
    assert (await unavailable.collect(COMPANY)).attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not service.requests
    client = CompaniesHouseClient(service.http, CLOCK, "fake")
    client.requests.extend([CLOCK.now()] * 599)
    assert (await CompaniesHouseOfficersProvider(client, CLOCK).collect(COMPANY)).items
    result = await CompaniesHousePscProvider(client, CLOCK).collect(COMPANY)
    await service.http.aclose()
    assert result.attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert len(service.requests) == 1


async def test_gleif_redirect_never_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(
        monkeypatch, response=httpx.Response(302, headers={"location": "http://127.0.0.1"})
    )
    result = await GleifParentProvider(service.http, CLOCK).collect(ENTITY)
    await service.http.aclose()
    assert len(service.requests) == 1 and result.attempts[0].status is CollectionStatus.FAILED


async def test_gleif_mismatched_profile_and_absent_relationship_are_not_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = gleif_profile()
    payload["data"]["attributes"]["lei"] = PARENT
    service = RecordService(monkeypatch, payload)
    profile = await GleifProfileProvider(service.http, CLOCK).collect(ENTITY)
    await service.http.aclose()
    assert not profile.items and profile.attempts[0].status is CollectionStatus.FAILED
    service = RecordService(monkeypatch, {"data": None})
    parent = await GleifParentProvider(service.http, CLOCK).collect(ENTITY)
    await service.http.aclose()
    assert not parent.items and parent.attempts[0].status is CollectionStatus.EMPTY
    assert "do not prove that no parent exists" in parent.attempts[0].explanation
