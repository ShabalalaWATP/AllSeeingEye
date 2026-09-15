"""Current typed Radar aggregates remain scoped, licensed and explicitly incomplete."""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research_records import cloudflare_radar
from ase.adapters.research_records.cloudflare_radar import CloudflareRadarResearchProvider
from ase.domain.events import Category, GeoConfidence
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_matches_time
from ase.domain.research import CollectionStatus, ResearchFocus
from ase.domain.research_area import direct_area_from_geometry
from cloudflare_radar_support import NOW, QUERY, payload, provider


async def test_explicit_current_snapshot_preserves_exact_provider_metadata_and_privacy():
    source, http = provider()
    batch = await source.collect(QUERY)
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(batch.items) == 3 and len(http.calls) == 1
    other = CloudflareRadarResearchProvider(
        source._reader, source._clock, layer="layer7", allow_noncommercial_data=True
    )
    other_batch = await other.collect(QUERY)
    assert len(other_batch.items) == 2 and len(http.calls) == 2
    assert all("dateRange=1d&limit=10&format=json" in url for url in http.calls)
    assert all(QUERY.question not in url and QUERY.terms[0] not in url for url in http.calls)
    assert all("offline-fixture-token" not in url for url in http.calls)
    layer3 = next(item for item in batch.items if item.attributes["layer"] == "layer3")
    layer7 = other_batch.items[0]
    assert layer3.attributes["period_start"] == "2026-09-13T09:45:00+00:00"
    assert layer3.attributes["period_end"] == "2026-09-14T09:45:00+00:00"
    assert layer3.attributes["dataset_updated_at"] == "2026-09-14T09:55:00+00:00"
    assert layer3.attributes["provider_version"] is None
    assert layer7.attributes["provider_version"] == "synthetic-provider-revision-2"
    assert layer3.attributes["api_version"] == "v4"
    assert json.loads(layer3.attributes["provider_units"]) == [{"name": "*", "value": "bytes"}]
    assert layer3.attributes["unit"] == "%" and layer3.attributes["share_percent"] == 41.125
    assert layer3.attributes["rank"] == 1 and layer3.observed_at == NOW
    assert layer3.observation.acquired_at.isoformat() == layer3.attributes["period_start"]
    assert layer3.published_at is None
    assert all(
        item.grade == "F6"
        and item.point is None
        and item.geometry is None
        and item.geo_confidence is GeoConfidence.COUNTRY
        for item in batch.items
    )
    assert all(item.category is Category.CYBER for item in batch.items)
    assert "billing country" in layer7.attributes["geography_basis"]
    assert layer3.attributes["attribution_status"] == "not_established"
    assert all(item.attributes["licence"] == "CC BY-NC 4.0" for item in batch.items)
    assert "Missing countries are unknown, not zero" in batch.attempts[0].explanation
    assert all(
        evidence_matches_time(item, QUERY.effective_time_basis, QUERY.since, QUERY.until)
        for item in batch.items
    )
    assert (await source.collect(QUERY)).items == batch.items
    assert len(http.calls) == 2  # The shared reader's cache prevents private query fan-out.


async def test_country_filter_retains_global_rank_denominator_and_actual_zero():
    source, http = provider()
    japan = await source.collect(replace(QUERY, country_iso="JP"))
    assert len(japan.items) == 1
    assert japan.items[0].attributes["share_percent"] == 0
    assert japan.items[0].attributes["rank"] == 3
    missing = await source.collect(replace(QUERY, country_iso="NZ"))
    assert not missing.items and missing.attempts[0].status is CollectionStatus.EMPTY
    assert "unknown, not zero" in missing.attempts[0].explanation
    assert len(http.calls) == 1


@pytest.mark.parametrize("subject", ["radar:global", "radar:GB"])
async def test_exact_subject_is_an_explicit_selection(subject):
    source, _ = provider()
    query = replace(QUERY, source_ids=None, subject=subject)
    assert source.supports(query)
    batch = await source.collect(query)
    assert batch.items
    if subject == "radar:GB":
        assert {item.country_iso for item in batch.items} == {"GB"}


@pytest.mark.parametrize(
    "changes",
    [
        {"source_ids": None},
        {"source_ids": ()},
        {"source_ids": ("unrelated",)},
        {"source_ids": (), "subject": "radar:GB"},
        {"subject": "radar:ZZ"},
        {"subject": "radar:GB", "country_iso": "FR"},
        {"subject": "radar:global", "country_iso": "GB"},
        {"subject": "https://private.example/secret"},
        {"subject": "corporate entity"},
        {"focus": ResearchFocus.COMPANY},
        {"focus": ResearchFocus.DOMAIN},
        {"focus": ResearchFocus.DOCUMENT},
        {"focus": ResearchFocus.MEDIA},
        {"languages": ("fr",)},
        {"time_basis": EvidenceTimeBasis.PUBLICATION},
        {"country_isos": ("GB", "FR")},
        {"since": NOW - timedelta(hours=12)},
        {"until": NOW - timedelta(days=1)},
        {"until": NOW + timedelta(days=1)},
    ],
)
async def test_unsupported_selection_scope_or_time_basis_never_calls_reader(changes):
    source, http = provider()
    query = replace(QUERY, **changes)
    assert not source.supports(query)
    result = await source.collect(query)
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not result.items and not http.calls


async def test_polygon_scope_is_not_widened_to_country_or_global_context():
    area = direct_area_from_geometry(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                    },
                }
            ],
        }
    )
    source, http = provider()
    result = await source.collect(replace(QUERY, area=area))
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not http.calls


@pytest.mark.parametrize("layer", ["layer3", "layer7"])
async def test_each_provider_has_a_fixed_id_layer_and_one_request_ceiling(layer):
    source, http = provider(layer=layer)
    assert source.id == f"research-cloudflare-radar-{layer}"
    result = await source.collect(QUERY)
    assert len(http.calls) == 1 and f"/{layer}/" in http.calls[0]
    assert {item.attributes["layer"] for item in result.items} == {layer}
    other = "layer3" if layer == "layer7" else "layer7"
    rejected = await source.collect(
        replace(QUERY, source_ids=(f"research-cloudflare-radar-{other}",))
    )
    assert rejected.attempts[0].status is CollectionStatus.UNSUPPORTED and len(http.calls) == 1


def test_unrecognised_provider_layer_is_rejected():
    with pytest.raises(ValueError):
        provider(layer="invented")


@pytest.mark.parametrize("allowed", [False, None, "false", 1])
async def test_noncommercial_acknowledgement_fails_closed_before_reader_call(allowed):
    source, http = provider(allowed=allowed)
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE and not http.calls
    assert "acknowledgement" in result.attempts[0].explanation


async def test_missing_credential_is_unavailable_without_network_or_secret_echo():
    source, http = provider(token=None)
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE and not http.calls
    assert "not_configured" in result.attempts[0].explanation


async def test_failed_layer_does_not_admit_other_layer_as_substitute():
    data = payload()
    data["layer7"]["result"]["meta"]["units"] = [{"name": "*", "value": "unknown"}]
    source, http = provider(data, layer="layer7")
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE and not result.items
    assert len(http.calls) == 1 and "/layer7/" in http.calls[0]
    other = CloudflareRadarResearchProvider(
        source._reader, source._clock, layer="layer3", allow_noncommercial_data=True
    )
    result = await other.collect(QUERY)
    assert {item.attributes["layer"] for item in result.items} == {"layer3"}
    assert "Collected layer3 only" in result.attempts[0].explanation
    assert len(http.calls) == 2


async def test_current_snapshot_is_not_clipped_to_requested_interval():
    source, http = provider()
    # The global reader is cached, but its earlier starts cannot be relabelled to this window.
    result = await source.collect(replace(QUERY, since=NOW - timedelta(days=1)))
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED and not result.items
    assert "no aggregate was clipped" in result.attempts[0].explanation
    assert len(http.calls) == 1


async def test_one_layer_fitting_scope_does_not_admit_the_other_partial_interval():
    source, _ = provider(layer="layer7")
    # Layer 7 ends at 09:30; layer 3 ends at 09:45. End is an inclusive provider bound.
    query = replace(QUERY, until=NOW - timedelta(minutes=15))
    result = await source.collect(query)
    assert {item.attributes["layer"] for item in result.items} == {"layer7"}
    assert "Collected layer7 only" in result.attempts[0].explanation


async def test_query_window_is_preserved_but_does_not_create_a_false_source_revision():
    source, _ = provider()
    first = await source.collect(QUERY)
    second_query = replace(QUERY, since=NOW - timedelta(days=7))
    second = await source.collect(second_query)
    assert first.items[0].id == second.items[0].id
    assert first.items[0].content_hash == second.items[0].content_hash
    assert first.items[0].attributes["query_since"] != second.items[0].attributes["query_since"]


@pytest.mark.parametrize(
    "error", [ValueError("sensitive provider message"), OSError("sensitive credential message")]
)
async def test_provider_failures_are_safely_redacted(error):
    class FailedReader:
        async def read_layer(self, layer):
            raise error

    source, _ = provider()
    source._reader = FailedReader()
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.FAILED
    assert "sensitive" not in repr(result)


async def test_reader_timeout_and_caller_cancellation_release_waiters(monkeypatch):
    stopped = asyncio.Event()

    class BlockedReader:
        async def read_layer(self, layer):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    source, _ = provider()
    source._reader = BlockedReader()
    monkeypatch.setattr(cloudflare_radar, "_TIMEOUT_SECONDS", 0.01)
    result = await source.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.TIMED_OUT and stopped.is_set()
    monkeypatch.setattr(cloudflare_radar, "_TIMEOUT_SECONDS", 10)
    task = asyncio.create_task(source.collect(QUERY))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
