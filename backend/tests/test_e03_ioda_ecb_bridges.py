"""Offline E03 contracts. Live endpoint smoke is recorded separately."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from ase.adapters.research_records.ecb_reference_rate import (
    API as ECB_API,
)
from ase.adapters.research_records.ecb_reference_rate import (
    EcbReferenceRateProvider,
)
from ase.adapters.research_records.ioda_outage_events import (
    API as IODA_API,
)
from ase.adapters.research_records.ioda_outage_events import (
    IodaOutageResearchProvider,
)
from ase.application.source_inventory import SourceRequirement
from ase.container.research import research_service
from ase.container.research_allocation_profiles import research_allocation_profiles
from ase.container.research_capabilities import research_capability_registry
from ase.container.research_sources import research_source_specs
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchQuery
from ase.domain.source_capabilities import DateSupport
from ase.domain.source_controls import source_control_keys

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)
SINCE = datetime(2026, 9, 12, tzinfo=UTC)
UNTIL = datetime(2026, 9, 14, tzinfo=UTC)
ECB_QUERY = ResearchQuery(
    "Private operator question",
    SINCE,
    UNTIL,
    subject="ECB:EXR:GBP",
    country_iso="GB",
    time_basis=EvidenceTimeBasis.RECORDED,
)
IODA_QUERY = ResearchQuery(
    "Private outage question",
    SINCE,
    UNTIL,
    subject="IODA:IR",
    country_iso="IR",
    time_basis=EvidenceTimeBasis.RECORDED,
)
ECB_HEADER = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,"
    "OBS_STATUS,OBS_CONF,UNIT,UNIT_MULT,SOURCE_AGENCY,TITLE_COMPL\n"
)


class Clock:
    def now(self):
        return NOW


class BytesHttp:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.requests = []

    async def get_bytes(self, url, *, conditional=True, max_redirects=3):
        self.requests.append((url, conditional, max_redirects))
        return self.payload


def ecb_row(day: str, value: str, *, key="EXR.D.GBP.EUR.SP00.A") -> str:
    return f"{key},D,GBP,EUR,SP00,A,{day},{value},A,F,GBP,0,4F0,GBP per EUR\n"


def ioda_payload(*, country="IR", from_time=None, until_time=None, rows=None):
    from_time = int(SINCE.timestamp()) if from_time is None else from_time
    until_time = int(UNTIL.timestamp()) if until_time is None else until_time
    return {
        "type": "outages.events",
        "error": None,
        "requestParameters": {
            "from": str(from_time),
            "until": str(until_time),
            "entityType": "country",
            "entityCode": country,
            "limit": 20,
        },
        "data": rows
        if rows is not None
        else [
            {
                "location": f"country/{country}",
                "start": int(SINCE.timestamp()) + 3600,
                "duration": 600,
                "datasource": "bgp",
                "method": "median",
                "location_name": "Iran",
            }
        ],
        "copyright": "Copyright (c) Georgia Tech Research Corporation",
    }


def test_ecb_daily_values_keep_units_missingness_and_observation_time():
    raw = (ECB_HEADER + ecb_row("2026-09-12", "0") + ecb_row("2026-09-13", "")).encode()
    http = BytesHttp(raw)
    batch = asyncio.run(EcbReferenceRateProvider(http, Clock()).collect(ECB_QUERY))
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(batch.items) == 2 and len(http.requests) == 1
    url, conditional, redirects = http.requests[0]
    assert url.startswith(ECB_API) and (conditional, redirects) == (False, 0)
    assert "Private" not in url
    params = parse_qs(urlparse(url).query)
    assert params == {
        "startPeriod": ["2026-09-12"],
        "endPeriod": ["2026-09-13"],
        "format": ["csvdata"],
    }
    first, second = batch.items
    assert first.attributes["value"] == 0.0 and first.attributes["missing_value"] is False
    assert second.attributes["value"] is None and second.attributes["missing_value"] is True
    assert first.attributes["unit"] == "GBP per EUR"
    assert first.attributes["source_agency"] == "4F0"
    assert first.attributes["revision_time"] is None
    assert first.published_at is None and first.observation is not None
    assert first.observation.acquired_at == SINCE and first.country_iso is None


@pytest.mark.parametrize(
    "query",
    [
        replace(ECB_QUERY, subject="ECB:EXR:USD"),
        replace(ECB_QUERY, time_basis=EvidenceTimeBasis.PUBLICATION),
        replace(ECB_QUERY, since=SINCE + timedelta(hours=1)),
        replace(ECB_QUERY, focus=ResearchFocus.COMPANY),
        replace(ECB_QUERY, country_iso="US", country_isos=("US",)),
        replace(ECB_QUERY, until=SINCE + timedelta(days=32)),
    ],
)
def test_ecb_unsupported_selection_does_not_dispatch(query):
    http = BytesHttp(b"")
    batch = asyncio.run(EcbReferenceRateProvider(http, Clock()).collect(query))
    assert batch.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not http.requests


@pytest.mark.parametrize(
    "raw",
    [
        ECB_HEADER + ecb_row("2026-09-12", "1", key="EXR.D.USD.EUR.SP00.A"),
        ECB_HEADER + ecb_row("2026-09-12", "NaN"),
        ECB_HEADER + ecb_row("2026-09-11", "1"),
        ECB_HEADER + ecb_row("2026-09-12", "1") + ecb_row("2026-09-12", "2"),
    ],
)
def test_ecb_wrong_series_invalid_value_or_date_fails_closed(raw):
    http = BytesHttp(raw.encode())
    batch = asyncio.run(EcbReferenceRateProvider(http, Clock()).collect(ECB_QUERY))
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert batch.items == () and len(http.requests) == 1


def test_ioda_requires_operator_data_use_review_before_any_request():
    http = BytesHttp(b"")
    batch = asyncio.run(IodaOutageResearchProvider(http, Clock()).collect(IODA_QUERY))
    assert batch.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not http.requests


def test_ioda_exact_country_window_and_signal_provenance():
    http = BytesHttp(json.dumps(ioda_payload()).encode())
    batch = asyncio.run(
        IodaOutageResearchProvider(http, Clock(), allow_data_use=True).collect(IODA_QUERY)
    )
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(http.requests) == 1 and len(batch.items) == 1
    url, conditional, redirects = http.requests[0]
    assert url.startswith(IODA_API) and (conditional, redirects) == (False, 0)
    assert "Private" not in url
    assert parse_qs(urlparse(url).query) == {
        "from": [str(int(SINCE.timestamp()))],
        "until": [str(int(UNTIL.timestamp()))],
        "entityType": ["country"],
        "entityCode": ["IR"],
        "limit": ["20"],
    }
    event = batch.items[0]
    assert event.attributes["signal"] == "bgp"
    assert event.attributes["duration_seconds"] == 600.0
    assert event.attributes["unit"] == "seconds"
    assert event.country_iso == "IR" and event.point is None
    assert event.published_at is None and event.observation is not None
    assert "not publication" in event.observation.limitations
    assert "cyberattack" in batch.attempts[0].explanation


def test_ioda_missing_duration_is_unknown_not_ongoing_or_zero():
    payload = ioda_payload()
    payload["data"][0]["duration"] = None
    http = BytesHttp(json.dumps(payload).encode())
    batch = asyncio.run(
        IodaOutageResearchProvider(http, Clock(), allow_data_use=True).collect(IODA_QUERY)
    )
    assert len(batch.items) == 1
    assert batch.items[0].attributes["window_end"] is None
    assert batch.items[0].attributes["duration_seconds"] is None
    assert "unknown time" in batch.items[0].summary


def test_ioda_outside_window_is_not_misreported_as_coverage():
    payload = ioda_payload()
    payload["data"][0]["start"] = int(SINCE.timestamp()) - 3600
    payload["data"][0]["duration"] = 600
    http = BytesHttp(json.dumps(payload).encode())
    batch = asyncio.run(
        IodaOutageResearchProvider(http, Clock(), allow_data_use=True).collect(IODA_QUERY)
    )
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    assert not batch.items


@pytest.mark.parametrize(
    "payload",
    [
        ioda_payload(country="RU"),
        ioda_payload(from_time=int(SINCE.timestamp()) + 1),
        ioda_payload(rows=[{"location": "country/IR", "start": "bad"}]),
        ioda_payload(
            rows=[
                {
                    "location": "country/IR",
                    "start": int(SINCE.timestamp()) + 3600,
                    "duration": -1,
                    "datasource": "bgp",
                    "method": "median",
                }
            ]
        ),
    ],
)
def test_ioda_mismatched_or_invalid_envelope_fails_closed(payload):
    http = BytesHttp(json.dumps(payload).encode())
    batch = asyncio.run(
        IodaOutageResearchProvider(http, Clock(), allow_data_use=True).collect(IODA_QUERY)
    )
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert batch.items == () and len(http.requests) == 1


def test_composed_ids_have_matching_source_specs_profiles_and_remaining_gaps():
    ids = {EcbReferenceRateProvider.id, IodaOutageResearchProvider.id}
    registry = research_capability_registry()
    specs = {row.id: row for row in research_source_specs()}
    profiles = research_allocation_profiles()
    providers = {row.id for row in research_service(BytesHttp(b""), Clock())._providers(IODA_QUERY)}
    assert ids <= registry.capabilities.keys() & specs.keys() & profiles.keys() & providers
    selected = registry.resolve(("MACRO", "NETWORK"))
    assert EcbReferenceRateProvider.id in selected.candidate_provider_ids
    assert IodaOutageResearchProvider.id not in selected.candidate_provider_ids
    approved = registry.resolve(
        ("NETWORK",),
        requirements={
            IodaOutageResearchProvider.id: SourceRequirement(
                "acknowledgement", True, "environment", None, "Offline permission fixture."
            )
        },
    )
    assert IodaOutageResearchProvider.id in approved.candidate_provider_ids
    assert registry.capabilities[IodaOutageResearchProvider.id].support.dates == (
        DateSupport.RECORDED_INTERVAL,
    )
    assert source_control_keys(IodaOutageResearchProvider.id) == (
        IodaOutageResearchProvider.id,
        "ioda_outage_events",
    )
    assert "Cloudflare outage annotations" in registry.gaps["gap.network_telemetry"].reason
    assert "other ONS and ECB series" in registry.gaps["gap.ons_ecb"].reason


def test_selected_ecb_route_is_collectable_through_research_service():
    http = BytesHttp((ECB_HEADER + ecb_row("2026-09-12", "0.85633")).encode())
    service = research_service(http, Clock())
    query = replace(ECB_QUERY, source_ids=(EcbReferenceRateProvider.id,))
    batch = asyncio.run(service.collect(query))
    assert len(http.requests) == 1
    assert len(batch.items) == 1
    assert batch.items[0].source_id == EcbReferenceRateProvider.id


def test_selected_ioda_route_stays_off_until_configured_in_service():
    http = BytesHttp(json.dumps(ioda_payload()).encode())
    query = replace(IODA_QUERY, source_ids=(IodaOutageResearchProvider.id,))
    disabled = research_service(http, Clock())
    batch = asyncio.run(disabled.collect(query))
    assert not http.requests and not batch.items
    enabled = research_service(http, Clock(), ioda_public_data_use_acknowledged=True)
    batch = asyncio.run(enabled.collect(query))
    assert len(http.requests) == 1 and len(batch.items) == 1
    assert batch.items[0].source_id == IodaOutageResearchProvider.id
