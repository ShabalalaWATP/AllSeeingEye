"""Procurement queries fetch one date-bounded page and make no identity/completeness claim."""

import json
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from ase.adapters.research_records.contracts_finder import ContractsFinderProvider
from ase.adapters.research_records.record_metadata import bounded_json
from ase.domain.research import CollectionStatus
from helpers import FakeClock
from research_records_helpers import CLOCK, QUERY, RecordService


def package(count: int = 1):
    return {
        "publishedDate": "2026-09-05T12:00:00Z",
        "license": "OGL 3.0",
        "releases": [
            {
                "ocid": f"ocds-b5fd17-notice-{index}",
                "id": f"release-{index}",
                "date": "2026-09-05T12:00:00Z",
                "tender": {
                    "title": "Rail maintenance",
                    "description": "Works notice",
                    "status": "active",
                },
                "buyer": {"name": "Example Council"},
                "awards": [{"suppliers": [{"name": "Example Supplier"}]}],
            }
            for index in range(count)
        ],
    }


async def test_one_public_page_local_matches_and_bounded_releases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, package(25))
    batch = await ContractsFinderProvider(service.http, CLOCK).collect(
        replace(QUERY, terms=("Example Supplier",))
    )
    await service.http.aclose()
    assert len(service.requests) == 1 and len(batch.items) == 20
    request = service.requests[0]
    assert request.url.path == "/Published/Notices/OCDS/Search"
    assert request.url.params["limit"] == "20"
    assert "Example Supplier" not in str(request.url) and QUERY.question not in str(request.url)
    assert batch.items[0].attributes["identity_match"] == "phrase_candidate_only"
    assert batch.items[0].attributes["declared_licence"] == "OGL 3.0"
    assert batch.items[0].grade == "F6"
    assert "not a complete procurement search" in batch.attempts[0].explanation


async def test_release_dates_and_nonmatching_names_are_excluded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = package(3)
    data["releases"][0]["date"] = "2020-01-01T00:00:00Z"
    data["releases"][1]["date"] = "2026-09-06T00:00:00Z"
    data["releases"][2]["date"] = "2026-09-05T12:00:00"  # no timezone
    service = RecordService(monkeypatch, data)
    provider = ContractsFinderProvider(service.http, CLOCK)
    assert not (await provider.collect(replace(QUERY, terms=("rail",)))).items
    await service.http.aclose()
    service = RecordService(monkeypatch, package())
    assert not (
        await ContractsFinderProvider(service.http, CLOCK).collect(
            replace(QUERY, terms=("unrelated",))
        )
    ).items
    await service.http.aclose()


async def test_403_failure_cooldown_stops_requests_for_five_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(
        monkeypatch, response=httpx.Response(403, text="private upstream details")
    )
    clock = FakeClock(CLOCK.now())
    provider = ContractsFinderProvider(service.http, clock)
    query = replace(QUERY, terms=("rail",))
    first = await provider.collect(query)
    assert first.attempts[0].status is CollectionStatus.FAILED
    assert "private upstream" not in repr(first)
    assert (await provider.collect(query)).attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert len(service.requests) == 1
    clock.advance(timedelta(minutes=5))
    await provider.collect(query)
    assert len(service.requests) == 2
    await service.http.aclose()


async def test_missing_explicit_terms_never_make_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(monkeypatch, package())
    result = await ContractsFinderProvider(service.http, CLOCK).collect(QUERY)
    await service.http.aclose()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED and not service.requests


def test_metadata_arrays_never_become_truncated_invalid_json():
    values = ["x" * 200] * 20
    encoded, omitted = bounded_json(values)
    assert len(encoded) <= 500
    assert len(json.loads(encoded)) + omitted == len(values)
    assert omitted > 0
