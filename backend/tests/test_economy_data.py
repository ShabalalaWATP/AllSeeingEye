"""Public data parsers preserve gaps, periods, units and bounded request identities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.economy.ecb import ECB_NAMESPACE, MAX_XML_BYTES, parse_ecb
from ase.adapters.economy.gateway import PublicEconomyGateway
from ase.adapters.economy.world_bank import MAX_ROWS, parse_world_bank, world_bank_url
from ase.adapters.feeds.http import FeedFetchError
from ase.application.economy_evidence import economy_evidence
from ase.domain.economy import EconomySnapshot
from ase.domain.economy_catalogue import INDICATORS, REGIONS
from helpers import FakeClock

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def wb_row(**changes):
    return {
        "countryiso3code": "GBR",
        "indicator": {"id": "NY.GDP.MKTP.CD"},
        "date": "2025",
        "value": 3_000_000_000_000,
        **changes,
    }


def wb_payload(*rows):
    return [{"page": 1, "pages": 1, "lastupdated": "2026-07-13"}, list(rows or [wb_row()])]


def fx_payload(content=None):
    return (
        f'<Envelope xmlns="{ECB_NAMESPACE}"><Cube>'
        + (
            content
            if content is not None
            else '<Cube time="2026-09-11"><Cube currency="GBP" rate="0.85"/>'
            '<Cube currency="USD" rate="1.1"/><Cube currency="CNY" rate="7.8"/></Cube>'
        )
        + "</Cube></Envelope>"
    ).encode()


def test_one_fixed_batch_query_and_twelve_observation_years():
    url = urlsplit(world_bank_url(NOW))
    assert url.hostname == "api.worldbank.org"
    assert "WLD;GBR;USA;RUS;CHN;IRN" in url.path
    query = parse_qs(url.query)
    assert query == {
        "source": ["2"],
        "format": ["json"],
        "date": ["2014:2025"],
        "per_page": [str(MAX_ROWS)],
        "page": ["1"],
    }
    result = parse_world_bank(wb_payload(wb_row(), wb_row(date="2024", value=None)), NOW)
    assert [region.id for region in result] == ["WORLD", "GB", "US", "RU", "CN", "IR"]
    gdp = result[1].series[0]
    assert gdp.status == "available" and len(gdp.points) == 12
    assert gdp.points[-2].value is None and gdp.points[-1].value == 3e12
    assert gdp.source_updated_at == "2026-07-13" and gdp.updated_at == NOW
    assert gdp.unit == "Current US dollars"
    assert result[-1].series[0].status == "unavailable"
    assert all(p.value is None for p in result[-1].series[0].points)


@pytest.mark.parametrize(
    "changes",
    [
        {"value": True},
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": "3"},
        {"value": 1e40},
        {"date": "2026"},
        {"date": "2013"},
        {"date": "\uff12\uff10\uff12\uff15"},
        {"date": None},
        {"countryiso3code": "ZZZ"},
        {"countryiso3code": []},
        {"indicator": {"id": "WRONG"}},
        {"indicator": []},
    ],
)
def test_untrusted_or_out_of_scope_observations_do_not_become_values(changes):
    with pytest.raises(ValueError, match="No recognised"):
        parse_world_bank(wb_payload(wb_row(**changes)), NOW)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [],
        [{}, []],
        [{"page": 1, "pages": 2}, []],
        [{"page": 1, "pages": 1}, [wb_row()] * (MAX_ROWS + 1)],
    ],
)
def test_invalid_or_truncated_batches_fail_closed(payload):
    with pytest.raises(ValueError):
        parse_world_bank(payload, NOW)


def test_conflicting_duplicate_is_rejected_and_bad_release_date_is_not_invented():
    with pytest.raises(ValueError, match="Contradictory"):
        parse_world_bank(wb_payload(wb_row(), wb_row(value=99)), NOW)
    data = wb_payload(wb_row(value=0))
    data[0]["lastupdated"] = "not a date"
    gdp = parse_world_bank(data, NOW)[1].series[0]
    assert gdp.source_updated_at is None and gdp.points[-1].value == 0


def test_ecb_history_has_named_base_units_and_unavailable_ruble_and_rial():
    result = parse_ecb(fx_payload(), NOW)
    assert result[0].points[0].value == 0.85
    assert result[0].unit == "GBP per EUR"
    assert result[0].source_updated_at == "2026-09-11"
    assert result[3].status == "unavailable" and "suspended" in result[3].note
    assert result[4].status == "unavailable" and not result[4].points


def test_ecb_dates_sorted_missing_currency_gaps_and_older_observation_label():
    raw = fx_payload(
        '<Cube time="2026-08-30"><Cube currency="GBP" rate="0.85"/></Cube>'
        '<Cube time="2026-08-29"><Cube currency="USD" rate="1.1"/></Cube>'
    )
    result = parse_ecb(raw, NOW)
    assert result[0].status == "stale"
    assert [p.date for p in result[0].points] == ["2026-08-29", "2026-08-30"]
    assert result[0].points[0].value is None
    assert result[2].status == "unavailable"


@pytest.mark.parametrize(
    "raw",
    [
        b'<!DOCTYPE x [<!ENTITY a "boom">]><x>&a;</x>',
        b"not XML",
        pytest.param(b"x" * (MAX_XML_BYTES + 1), id="oversized-xml"),
        fx_payload(""),
        fx_payload(
            '<Cube time="2026-09-11"><Cube currency="GBP" rate="1"/>'
            '<Cube currency="GBP" rate="2"/></Cube>'
        ),
        fx_payload('<Cube time="2026-09-11"/><Cube time="2026-09-11"/>'),
        fx_payload('<Cube time="2099-01-01"><Cube currency="GBP" rate="1"/></Cube>'),
        fx_payload('<Cube time="2026-09-11"><Cube currency="GBP" rate="nan"/></Cube>'),
    ],
)
def test_invalid_ecb_inputs_fail_without_synthetic_rates(raw):
    with pytest.raises(ValueError):
        parse_ecb(raw, NOW)


async def test_gateway_uses_guarded_clients_without_redirects_or_conditions():
    http = AsyncMock()
    http.get_json.return_value = wb_payload()
    http.get_bytes.return_value = fx_payload()
    gateway = PublicEconomyGateway(http, FakeClock(NOW))
    assert await gateway.macro()
    assert await gateway.fx()
    assert http.get_json.call_args.kwargs == {"conditional": False, "max_redirects": 0}
    assert http.get_bytes.call_args.kwargs == {"conditional": False, "max_redirects": 0}
    http.get_bytes.side_effect = FeedFetchError("untrusted upstream body")
    with pytest.raises(ValueError, match="temporarily unavailable") as error:
        await gateway.fx()
    assert "untrusted" not in str(error.value)


def test_evidence_preserves_observation_period_and_unassessed_grade():
    snapshot = EconomySnapshot(
        NOW,
        NOW + timedelta(hours=1),
        parse_world_bank(wb_payload(), NOW),
        parse_ecb(fx_payload(), NOW),
    )
    events = economy_evidence(snapshot, NOW)
    assert len(events) == 4
    assert all(event.grade == "F6" for event in events)
    annual = next(event for event in events if event.source_id == "research-world-bank")
    assert "2025" in annual.summary and annual.country_iso == "GB"
    assert all(event.published_at is None for event in events)
    assert all(event.observed_at == NOW for event in events)
    assert "not the observation date" in annual.summary
    assert annual.attributes["region"] == "GB"
    assert annual.attributes["gdp_observation_period"] == "2025"
    assert annual.attributes["gdp_source_updated_at"] == "2026-07-13"
    currency = next(event for event in events if event.source_id == "economic-ecb")
    assert currency.attributes["observation_period"] == "2026-09-11"
    assert currency.attributes["source_updated_at"] == "2026-09-11"
    assert {event.source_id for event in events} == {"research-world-bank", "economic-ecb"}


def test_macro_evidence_fits_source_cap_without_losing_any_region():
    rows = [
        wb_row(
            countryiso3code=code,
            indicator={"id": indicator},
            value=10 + index,
            date=str(2025 - index),
        )
        for _, _, code in REGIONS
        for index, (_, _, indicator, _) in enumerate(INDICATORS)
    ]
    snapshot = EconomySnapshot(
        NOW,
        NOW + timedelta(hours=1),
        parse_world_bank(wb_payload(*rows), NOW),
        parse_ecb(fx_payload(), NOW),
    )
    events = economy_evidence(snapshot, NOW)
    assert len(events) == 9
    macro = [event for event in events if event.source_id == "research-world-bank"]
    assert len(macro) == 6
    for event in macro:
        assert len(event.summary) <= 2000
        assert all(str(year) in event.summary for year in (2022, 2023, 2024, 2025))
        assert all(label in event.summary for _, label, _, _ in INDICATORS)
        assert "source=2" in event.url and "per_page=48" in event.url
