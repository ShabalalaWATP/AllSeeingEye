"""Provider-schema boundaries and conservative typed-snapshot admission."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.radar_attack_trends import (
    RadarAttackSnapshot,
    RadarAttackTrends,
    RadarAttackUnit,
)
from ase.api.schemas_cyber import RadarAttackSnapshotOut
from ase.domain.research import CollectionStatus
from cloudflare_radar_support import NOW, QUERY, RadarHttp, payload, provider
from helpers import FakeClock


@pytest.mark.parametrize(
    ("layer", "unit"), [("layer3", "bytes"), ("layer3", "requests"), ("layer7", "requests")]
)
async def test_reader_uses_actual_recognised_provider_units(layer, unit):
    data = payload()
    data[layer]["result"]["meta"]["units"] = [{"name": "*", "value": unit}]
    reader = RadarAttackTrends(RadarHttp(data), FakeClock(NOW), "offline-fixture-token")
    parsed = await reader._fetch(layer)
    assert parsed.unit == unit
    assert parsed.provider_units == (RadarAttackUnit("*", unit),)
    assert parsed.updated_at != parsed.period_to
    if layer == "layer3":
        assert parsed.provider_version is None


async def test_valid_provider_response_preserves_existing_dashboard_dto():
    source, _ = provider()
    snapshot = await source._reader.read()
    model = RadarAttackSnapshotOut.model_validate(snapshot)
    assert model.status == "ready" and len(model.layers) == 2
    assert model.layers[0].unit == snapshot.layers[0].provider_units[0].value
    assert model.layers[0].updated_at == snapshot.layers[0].updated_at


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("units", None),
        ("units", []),
        ("units", [{"name": "*", "value": "packets"}]),
        ("units", [{"name": "top_0", "value": "bytes"}]),
        ("units", [{"name": "*", "value": "bytes"}] * 2),
        ("units", ["bytes"]),
        ("lastUpdated", None),
        ("lastUpdated", "not a date"),
        ("lastUpdated", "2026-09-14T09:55:00"),
        ("normalization", "RAW_VALUES"),
        ("dateRange", []),
        ("dateRange", "1d"),
        ("dateRange", [{"startTime": "bad", "endTime": "2026-09-14T09:45:00Z"}]),
        ("dateRange", [{"startTime": "2026-09-12T09:45:00Z", "endTime": "2026-09-14T09:45:00Z"}]),
        ("version", 123),
        ("version", ""),
        ("version", "x" * 101),
        ("version", "bad\x00version"),
    ],
)
async def test_reader_rejects_nonconforming_metadata(field, value):
    data = payload()
    data["layer3"]["result"]["meta"][field] = value
    reader = RadarAttackTrends(RadarHttp(data), FakeClock(NOW), "offline-fixture-token")
    with pytest.raises(FeedFetchError):
        await reader._fetch("layer3")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rank", 0),
        ("rank", True),
        ("rank", 11),
        ("rank", 2),
        ("targetCountryAlpha2", "ZZ"),
        ("targetCountryAlpha2", "gb"),
        ("targetCountryName", ""),
        ("value", "nan"),
        ("value", True),
        ("value", "invalid number"),
        ("value", -1),
        ("value", 101),
        ("value", None),
    ],
)
async def test_reader_rejects_invalid_row_instead_of_silently_dropping_it(field, value):
    data = payload()
    data["layer3"]["result"]["top_0"][0][field] = value
    reader = RadarAttackTrends(RadarHttp(data), FakeClock(NOW), "offline-fixture-token")
    with pytest.raises(FeedFetchError):
        await reader._fetch("layer3")


@pytest.mark.parametrize(
    "mutation",
    [
        "too_many",
        "empty",
        "bad_row",
        "duplicate_country",
        "total",
        "multiple_ranges",
        "bad_result",
        "failed",
    ],
)
async def test_reader_rejects_broken_envelopes_or_rankings(mutation):
    data = payload()
    result = data["layer3"]["result"]
    if mutation == "too_many":
        result["top_0"] *= 4
    elif mutation == "empty":
        result["top_0"] = []
    elif mutation == "bad_row":
        result["top_0"][0] = "not a country"
    elif mutation == "duplicate_country":
        result["top_0"][1]["targetCountryAlpha2"] = "GB"
    elif mutation == "total":
        result["top_0"][0]["value"] = 100
    elif mutation == "multiple_ranges":
        result["meta"]["dateRange"] *= 2
    elif mutation == "bad_result":
        data["layer3"]["result"] = []
    else:
        data["layer3"]["success"] = False
    reader = RadarAttackTrends(RadarHttp(data), FakeClock(NOW), "offline-fixture-token")
    with pytest.raises(FeedFetchError):
        await reader._fetch("layer3")


async def test_incompatible_layer7_units_are_not_relabelled_as_requests():
    data = payload()
    data["layer7"]["result"]["meta"]["units"] = [{"name": "*", "value": "bytes"}]
    reader = RadarAttackTrends(RadarHttp(data), FakeClock(NOW), "offline-fixture-token")
    with pytest.raises(FeedFetchError):
        await reader._fetch("layer7")


async def test_completed_fetch_time_is_retained_separately_from_request_start():
    clock = FakeClock(NOW)

    class SlowHttp(RadarHttp):
        async def get_json(self, *args, **kwargs):
            clock.advance(timedelta(seconds=1))
            return await super().get_json(*args, **kwargs)

    reader = RadarAttackTrends(SlowHttp(), clock, "offline-fixture-token")
    result = await reader.read()
    assert result.fetched_at == NOW + timedelta(seconds=1)
    assert (await reader.read_layer("layer3")).fetched_at == NOW + timedelta(seconds=1)
    assert (await reader.read_layer("layer7")).fetched_at == NOW + timedelta(seconds=2)
    assert all(layer.updated_at < result.fetched_at for layer in result.layers)


async def test_cached_stale_data_is_not_accepted_as_current_research_coverage():
    source, http = provider()
    assert (await source.collect(QUERY)).items
    source._clock.advance(timedelta(minutes=31))
    http.data = {"layer3": {"success": False}, "layer7": {"success": False}}
    newer = replace(QUERY, until=NOW + timedelta(minutes=31))
    result = await source.collect(newer)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "stale" in result.attempts[0].explanation and not result.items
    source._clock.advance(timedelta(hours=3))
    expired = await source._reader.read_layer(source.layer)
    assert expired.status == "unavailable" and not expired.layers


@pytest.mark.parametrize(
    "change",
    [
        {"status": "disabled"},
        {"status": "not_configured"},
        {"status": "unavailable"},
        {"status": "stale"},
    ],
)
async def test_unavailable_reader_states_fail_closed(change):
    source, _ = provider()
    snapshot = RadarAttackSnapshot(
        **({"status": "ready", "fetched_at": NOW, "layers": ()} | change)
    )

    class Reader:
        async def read_layer(self, layer):
            return snapshot

    source._reader = Reader()
    assert (await source.collect(QUERY)).attempts[0].status is CollectionStatus.UNAVAILABLE


@pytest.mark.parametrize(
    "mutation",
    [
        "no_fetched",
        "naive_fetched",
        "future_fetched",
        "expired_fetched",
        "no_layers",
        "duplicate_layers",
        "unexpected_two_layers",
        "unknown_status",
        "missing_units",
        "changed_unit",
        "missing_updated",
        "future_updated",
        "old_updated",
        "bad_period",
        "future_period",
        "naive_period",
        "unknown_layer",
        "oversized_version",
        "duplicate_country",
        "bad_country",
        "nan_share",
        "boolean_share",
        "boolean_rank",
        "oversized_name",
        "excess_total",
    ],
)
async def test_adapter_revalidates_typed_data_before_releasing_evidence(mutation):
    source, _ = provider()
    original = await source._reader.read_layer(source.layer)
    layer = original.layers[0]
    changes = {
        "no_fetched": {"fetched_at": None},
        "naive_fetched": {"fetched_at": NOW.replace(tzinfo=None)},
        "future_fetched": {"fetched_at": NOW + timedelta(seconds=1)},
        "expired_fetched": {"fetched_at": NOW - timedelta(hours=3)},
        "no_layers": {"layers": ()},
        "duplicate_layers": {"layers": (layer, layer)},
        "unexpected_two_layers": {"layers": (layer, replace(layer, layer="layer7"))},
        "unknown_status": {"status": "invented"},
    }
    layer_changes = {
        "missing_units": {"provider_units": ()},
        "changed_unit": {"unit": "requests"},
        "missing_updated": {"updated_at": None},
        "future_updated": {"updated_at": NOW + timedelta(seconds=1)},
        "old_updated": {"updated_at": layer.period_from - timedelta(days=1)},
        "bad_period": {"period_from": layer.period_to},
        "future_period": {"period_to": NOW + timedelta(minutes=1)},
        "naive_period": {"period_from": layer.period_from.replace(tzinfo=None)},
        "unknown_layer": {"layer": "layer9"},
        "oversized_version": {"provider_version": "x" * 101},
        "duplicate_country": {"countries": (layer.countries[0], layer.countries[0])},
    }
    country_changes = {
        "bad_country": {"country_iso": "ZZ"},
        "nan_share": {"share_percent": float("nan")},
        "boolean_share": {"share_percent": True},
        "boolean_rank": {"rank": True},
        "oversized_name": {"country_name": "x" * 81},
        "excess_total": {"share_percent": 100},
    }
    if mutation in changes:
        snapshot = replace(original, **changes[mutation])
    else:
        if mutation in country_changes:
            changed_country = replace(layer.countries[0], **country_changes[mutation])
            changed_layer = replace(layer, countries=(changed_country, *layer.countries[1:]))
        else:
            changed_layer = replace(layer, **layer_changes[mutation])
        snapshot = replace(original, layers=(changed_layer,))

    class Reader:
        async def read_layer(self, layer):
            return snapshot

    source._reader = Reader()
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.FAILED and not result.items


async def test_dashboard_and_per_layer_reads_share_cache_without_extra_requests():
    http = RadarHttp()
    reader = RadarAttackTrends(http, FakeClock(NOW), "offline-fixture-token")
    readings = await asyncio.gather(
        reader.read_layer("layer3"), reader.read_layer("layer3"), reader.read()
    )
    assert readings[0] is readings[1]
    assert readings[2].status == "ready" and len(readings[2].layers) == 2
    assert len(http.calls) == 2
    assert (await reader.read_layer("layer7")).status == "ready"
    assert len(http.calls) == 2


async def test_combined_dashboard_preserves_stale_fallback_after_failed_refresh():
    http, clock = RadarHttp(), FakeClock(NOW)
    reader = RadarAttackTrends(http, clock, "offline-fixture-token")
    original = await reader.read()
    clock.advance(timedelta(minutes=31))
    http.data = {"layer3": {"success": False}, "layer7": {"success": False}}
    stale = await reader.read()
    assert stale.status == "stale" and stale.layers == original.layers
    assert stale.fetched_at == original.fetched_at
    assert len(http.calls) == 4


async def test_unsupported_layer_never_builds_an_arbitrary_endpoint():
    source, http = provider()
    with pytest.raises(ValueError):
        await source._reader.read_layer("../metadata")
    assert not http.calls
