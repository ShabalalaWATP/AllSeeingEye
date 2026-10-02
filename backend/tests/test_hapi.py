"""HAPI v2 shape fixtures, frozen provenance and request-local identity bounds."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import httpx
import pytest

from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from ase.adapters.research_records.hapi import HapiProvider
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_records import evidence_from_list, evidence_to_list
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, QUERY, RecordService

IDENTIFIER = "synthetic-app-identifier"
COUNTRIES = {"UA": "UKR"}
QUERY_UA = replace(QUERY, country_iso="UA")


def row():
    return {
        "resource_hdx_id": "12345678-1234-4123-8123-123456789abc",
        "location_code": "UKR",
        "admin_level": 1,
        "admin1_code": "UA01",
        "admin1_name": "Example region",
        "admin2_code": None,
        "admin2_name": None,
        "reference_period_start": "2026-09-01T00:00:00",
        "reference_period_end": "2026-09-06T00:00:00",
        "population": 123,
        "reporting_round": 1,
        "assessment_type": "baseline",
        "operation": "Example",
        "population_in_phase": 12,
        "population_fraction_in_phase": 0.2,
        "ipc_phase": "3",
        "ipc_type": "current",
        "org_name": "Example agency",
        "sector_name": "Food security",
    }


@pytest.mark.parametrize("topic", ["idps", "food-security", "operational-presence"])
async def test_topic_shape_is_frozen_without_private_question_or_identifier(monkeypatch, topic):
    service = RecordService(monkeypatch, {"data": [row()]})
    try:
        batch = await HapiProvider(service.http, CLOCK, topic, COUNTRIES, IDENTIFIER).collect(
            QUERY_UA
        )
        assert batch.attempts[0].status is CollectionStatus.COMPLETED
        event = batch.items[0]
        item = EvidenceItem.from_event(
            "E1", event, CLOCK.now(), source_name="HAPI", independence_key="IOM"
        )
        [restored] = evidence_from_list(evidence_to_list((item,)))
        attributes = {value.key: value.value for value in restored.attributes}
        assert attributes["admin_level"] == 1
        assert attributes["period_start"] == "2026-09-01T00:00:00+00:00"
        assert attributes["dataset_resource_id"] == row()["resource_hdx_id"]
        assert attributes["unit"] in ("people", "organisation-sector-location record")
        assert attributes["independent_conflict_corroboration"] is False
        assert restored.observation == event.observation and restored.published_at is None
        assert IDENTIFIER not in repr(batch)
        [request] = service.requests
        assert request.headers["X-HDX-HAPI-APP-IDENTIFIER"] == IDENTIFIER
        assert parse_qs(request.url.query.decode())["limit"] == ["20"]
        assert QUERY.question not in str(request.url) and IDENTIFIER not in str(request.url)
        assert "conflict" not in request.url.path
    finally:
        await service.http.aclose()


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"data": []}, CollectionStatus.EMPTY),
        ({"data": [row()] * 21}, CollectionStatus.FAILED),
        ({"data": [dict(row(), population=float("inf"))]}, CollectionStatus.FAILED),
        ({"data": [dict(row(), location_code="USA")]}, CollectionStatus.FAILED),
    ],
)
async def test_empty_and_invalid_are_distinct(monkeypatch, payload, status):
    # Invalid JSON numbers are simulated at the application boundary separately.

    http = AsyncMock()
    http.get_json.return_value = payload
    batch = await HapiProvider(http, CLOCK, "idps", COUNTRIES, IDENTIFIER).collect(QUERY_UA)
    assert batch.attempts[0].status is status


async def test_unavailable_and_unsupported_never_fetch(monkeypatch):
    service = RecordService(monkeypatch, {})
    try:
        provider = HapiProvider(service.http, CLOCK, "idps", COUNTRIES)
        assert (await provider.collect(QUERY_UA)).attempts[0].status is CollectionStatus.UNAVAILABLE
        assert (await provider.collect(QUERY)).attempts[0].status is CollectionStatus.UNSUPPORTED
        assert not service.requests
    finally:
        await service.http.aclose()


async def test_hapi_header_never_leaks_to_other_providers_or_shared_client(monkeypatch):
    service = RecordService(monkeypatch, {})
    credential = FeedCredential("https://hapi.humdata.org", IDENTIFIER, "X-HDX-HAPI-APP-IDENTIFIER")
    try:
        await asyncio.gather(
            service.http.get_json("https://hapi.humdata.org/data", credential=credential),
            service.http.get_json("https://public.example/data"),
        )
        headers = {
            request.url.host: request.headers.get("X-HDX-HAPI-APP-IDENTIFIER")
            for request in service.requests
        }
        assert headers == {"hapi.humdata.org": IDENTIFIER, "public.example": None}
        with pytest.raises(FeedFetchError):
            await service.http.get_json("https://public.example/data", credential=credential)
        assert IDENTIFIER not in repr(credential)
    finally:
        await service.http.aclose()
    async with httpx.AsyncClient(headers={"X-HDX-HAPI-APP-IDENTIFIER": IDENTIFIER}) as shared:
        with pytest.raises(ValueError):
            FeedHttpClient("tests", client=shared)
