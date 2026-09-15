"""Offline ONS CPIH contract tests; no ONS service calls are made."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ase.adapters.research_records.ons_cpih import (
    AGGREGATE,
    API,
    MAX_JSON_BYTES,
    OnsCpihProvider,
)
from ase.application.research.reserved_collection import eligible_for_query
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchQuery

FIXTURES = Path(__file__).parent / "fixtures" / "research"


class FrozenClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 14, 12, tzinfo=UTC)


CLOCK = FrozenClock()


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class OfflineBytes:
    def __init__(self, *payloads: dict[str, Any] | bytes) -> None:
        self.payloads = list(payloads)
        self.requests: list[tuple[str, bool, int]] = []

    async def get_bytes(
        self, url: str, *, conditional: bool = True, max_redirects: int = 3
    ) -> bytes:
        self.requests.append((url, conditional, max_redirects))
        value = self.payloads.pop(0)
        return value if isinstance(value, bytes) else json.dumps(value).encode()


QUERY = ResearchQuery(
    question="Private question which must not enter the ONS URL",
    since=datetime(2026, 7, 1, tzinfo=UTC),
    until=datetime(2026, 10, 1, tzinfo=UTC),
    country_iso="GB",
    subject="ONS:CPIH:42",
    time_basis=EvidenceTimeBasis.RECORDED,
)


def test_collects_fixed_series_and_preserves_zero_null_and_version() -> None:
    http = OfflineBytes(fixture("ons_cpih_observations.json"))
    batch = asyncio.run(OnsCpihProvider(http, CLOCK).collect(QUERY))

    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(batch.items) == 3
    assert len(http.requests) == 1
    assert http.requests[0][1:] == (False, 0)
    assert http.requests[0][0].startswith(f"{API}/editions/time-series/versions/42/observations?")
    assert "time=%2A" in http.requests[0][0]
    assert f"aggregate={AGGREGATE}" in http.requests[0][0]
    assert "Private" not in str(http.requests)
    by_period = {item.attributes["observation_period"]: item for item in batch.items}
    assert by_period["Jul-26"].attributes["value"] == 0.0
    assert by_period["Jul-26"].attributes["missing_value"] is False
    assert by_period["Aug-26"].attributes["value"] is None
    assert by_period["Aug-26"].attributes["missing_value"] is True
    assert by_period["Sep-26"].attributes["dataset_version"] == "42"
    assert by_period["Sep-26"].published_at is None
    assert by_period["Sep-26"].observation is not None
    assert by_period["Sep-26"].observation.acquired_at == datetime(2026, 9, 1, tzinfo=UTC)
    assert by_period["Sep-26"].country_iso == "GB"
    assert "Open Government Licence" in batch.attempts[0].explanation


@pytest.mark.parametrize(
    "query",
    [
        replace(QUERY, subject="ONS:CPIH"),
        replace(QUERY, subject="ONS:CPIH:0"),
        replace(QUERY, subject="ONS:OTHER:42"),
        replace(QUERY, country_iso="US", country_isos=("US",)),
        replace(QUERY, focus=ResearchFocus.COMPANY),
        replace(QUERY, time_basis=EvidenceTimeBasis.PUBLICATION),
    ],
)
def test_unsupported_scope_makes_no_request(query: ResearchQuery) -> None:
    http = OfflineBytes()
    batch = asyncio.run(OnsCpihProvider(http, CLOCK).collect(query))
    assert batch.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert http.requests == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.update(offset=1),
        lambda data: data.update(total_observations=3),
        lambda data: data["dimensions"]["aggregate"]["option"].update(id="other"),
        lambda data: data["dimensions"]["geography"]["option"].update(id="US"),
        lambda data: data["links"]["version"].update(id="41"),
        lambda data: data["dimensions"]["time"]["options"].append({"id": "Oct-26"}),
        lambda data: data["observations"][0].update(observation="NaN"),
        lambda data: data.update(unit_of_measure=""),
    ],
)
def test_rejects_mismatched_or_malformed_observations(mutate: Any) -> None:
    observations = fixture("ons_cpih_observations.json")
    mutate(observations)
    http = OfflineBytes(observations)
    batch = asyncio.run(OnsCpihProvider(http, CLOCK).collect(QUERY))
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert batch.items == ()
    assert len(http.requests) == 1


def test_rejects_oversized_json_before_decoding() -> None:
    http = OfflineBytes(b"{" + b"x" * MAX_JSON_BYTES)
    batch = asyncio.run(OnsCpihProvider(http, CLOCK).collect(QUERY))
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert len(http.requests) == 1


def test_recorded_time_filter_and_evidence_preserve_truthful_month_anchor() -> None:
    http = OfflineBytes(fixture("ons_cpih_observations.json"))
    batch = asyncio.run(OnsCpihProvider(http, CLOCK).collect(QUERY))
    september = next(
        item for item in batch.items if item.attributes["observation_period"] == "Sep-26"
    )

    assert eligible_for_query(september, QUERY)
    before = replace(
        QUERY,
        since=datetime(2026, 8, 1, tzinfo=UTC),
        until=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert not eligible_for_query(september, before)
    evidence = EvidenceItem.from_event(
        "E1", september, CLOCK.now(), source_name=OnsCpihProvider.name, independence_key="ons"
    )
    assert evidence.published_at is None
    assert evidence.observation == september.observation
    assert "not a measurement" in evidence.observation.limitations
