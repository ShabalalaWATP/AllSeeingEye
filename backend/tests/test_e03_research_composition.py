"""E03 factories use real IDs, explicit licence consent and one-request provider contracts."""

from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import Mock

import pytest

from ase.adapters.feeds.radar_attack_trends import RadarAttackTrends
from ase.adapters.research_records.cloudflare_radar import PROVIDER_IDS
from ase.adapters.research_records.ons_cpih import OnsCpihProvider
from ase.application.source_capabilities import CapabilityReadiness
from ase.application.source_inventory import SourceRequirement
from ase.container.research import research_service
from ase.container.research_allocation_profiles import research_allocation_profiles
from ase.container.research_capabilities import research_capability_registry
from ase.container.research_sources import research_source_specs
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus
from ase.domain.source_capabilities import DateSupport
from ase.domain.source_controls import source_control_keys
from cloudflare_radar_support import NOW, QUERY, RadarHttp
from helpers import FakeClock
from test_ons_cpih_research import CLOCK as ONS_CLOCK
from test_ons_cpih_research import QUERY as ONS_QUERY
from test_ons_cpih_research import OfflineBytes, fixture

RADAR_PARENT = "cloudflare_radar_attack_trends"
RADAR_IDS = tuple(PROVIDER_IDS.values())


class Admission:
    def __init__(self):
        self.disabled = set()

    async def enabled(self, key):
        return not self.disabled.intersection(source_control_keys(key))

    async def enabled_many(self, keys):
        return {key: await self.enabled(key) for key in keys}

    @asynccontextmanager
    async def guard(self):
        yield


def requirements(allowed=True):
    return {
        key: SourceRequirement(
            "acknowledgement",
            allowed,
            "environment",
            None,
            "Synthetic token presence and explicit noncommercial acknowledgement.",
        )
        for key in RADAR_IDS
    }


def radar_query(layer=None):
    return replace(
        QUERY,
        question="What do current Radar attack distributions show?",
        subject="radar:global",
        source_ids=(PROVIDER_IDS[layer],) if layer else RADAR_IDS,
    )


def radar_service(*, allowed=False, admission=None, supplied_reader=True):
    http, clock = RadarHttp(), FakeClock(NOW)
    reader = RadarAttackTrends(http, clock, "offline-fixture-token")
    service = research_service(
        http,
        clock,
        admission=admission,
        radar_reader=reader if supplied_reader else None,
        radar_noncommercial_use_acknowledged=allowed,
        requirements=requirements(),
    )
    return service, reader, http


def test_all_registries_include_the_exact_new_provider_ids_and_limits():
    ids = {OnsCpihProvider.id, *RADAR_IDS}
    specs = {row.id: row for row in research_source_specs()}
    registry, profiles = research_capability_registry(), research_allocation_profiles()
    service, _, _ = radar_service()
    providers = {row.id: row for row in service._providers(radar_query())}
    assert ids <= providers.keys() & specs.keys() & registry.capabilities.keys() & profiles.keys()
    assert all(registry.capabilities[key].provider_id == key for key in ids)
    assert all(specs[key].rating.assessed_grade is None for key in ids)
    assert all(profiles[key].primary_content for key in ids)
    assert registry.capabilities[OnsCpihProvider.id].support.dates == (
        DateSupport.RECORDED_INTERVAL,
    )
    for key in RADAR_IDS:
        assert specs[key].requires_key and "CC BY-NC 4.0" in specs[key].licence_note
        assert registry.capabilities[key].support.dates == (
            DateSupport.RESEARCH_INTERVAL,
            DateSupport.RECORDED_INTERVAL,
        )
        assert source_control_keys(key) == (key, RADAR_PARENT)
    assert {
        row.capability.origin_group
        for row in registry.resolve(("NETWORK",)).capabilities
        if row.capability.id in RADAR_IDS
    } == {"Cloudflare Radar"}


def test_bundles_disclose_remaining_gaps_without_denying_implemented_routes():
    registry = research_capability_registry()
    assert OnsCpihProvider.id in registry.resolve(("MACRO",)).candidate_provider_ids
    assert set(RADAR_IDS) <= {row.capability.id for row in registry.resolve(("CTI",)).capabilities}
    assert not set(RADAR_IDS) & set(registry.resolve(("NETWORK",)).candidate_provider_ids)
    ready = registry.resolve(("NETWORK",), requirements=requirements())
    assert set(RADAR_IDS) <= set(ready.candidate_provider_ids)
    assert all(
        row.readiness is CapabilityReadiness.CONFIGURED_UNVERIFIED
        for row in ready.capabilities
        if row.capability.id in RADAR_IDS
    )
    assert "Latest-version discovery" in registry.gaps["gap.ons_ecb"].reason
    assert "Cloudflare outage annotations" in registry.gaps["gap.network_telemetry"].reason


@pytest.mark.asyncio
async def test_actual_ons_collection_retains_observation_months_with_one_request():
    http = OfflineBytes(fixture("ons_cpih_observations.json"))
    service = research_service(http, ONS_CLOCK, admission=Admission())
    query = replace(
        ONS_QUERY, source_ids=(OnsCpihProvider.id,), time_basis=EvidenceTimeBasis.RECORDED
    )
    batch = await service.collect(query)
    assert len(http.requests) == 1 and http.requests[0][1:] == (False, 0)
    assert len(batch.items) == 3
    assert {item.attributes["dataset_version"] for item in batch.items} == {"42"}
    assert all(item.published_at is None and item.observation is not None for item in batch.items)
    assert "Private" not in http.requests[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("subject", ["ONS:CPIH", "ONS:CPIH:0", None])
async def test_actual_ons_collection_never_discovers_or_guesses_version(subject):
    http = OfflineBytes()
    service = research_service(http, ONS_CLOCK, admission=Admission())
    query = replace(
        ONS_QUERY,
        subject=subject,
        source_ids=(OnsCpihProvider.id,),
        time_basis=EvidenceTimeBasis.RECORDED,
    )
    batch = await service.collect(query)
    assert not http.requests and not batch.items
    assert (
        next(row for row in batch.attempts if row.source_id == OnsCpihProvider.id).status
        is CollectionStatus.UNSUPPORTED
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("layer", ["layer3", "layer7"])
async def test_actual_radar_collection_preserves_layer_and_shared_single_request_cache(layer):
    service, reader, http = radar_service(allowed=True, admission=Admission())
    query = radar_query(layer)
    batch = await service.collect(query)
    assert len(http.calls) == 1 and f"/{layer}/" in http.calls[0]
    assert batch.items and {item.attributes["layer"] for item in batch.items} == {layer}
    assert all(item.published_at is None and item.point is None for item in batch.items)
    assert query.terms[0] not in http.calls[0]
    again = await service.collect(query)
    assert again.items == batch.items and len(http.calls) == 1
    assert (await reader.read_layer(layer)).status == "ready" and len(http.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed,supplied_reader", [(False, True), (1, True), (True, False)])
async def test_token_or_external_readiness_never_substitutes_for_explicit_consent(
    allowed, supplied_reader
):
    service, _, http = radar_service(
        allowed=allowed, admission=Admission(), supplied_reader=supplied_reader
    )
    batch = await service.collect(radar_query("layer3"))
    assert not http.calls and not batch.items
    row = next(row for row in batch.attempts if row.source_id == PROVIDER_IDS["layer3"])
    assert row.status is CollectionStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_default_legacy_factory_is_unavailable_without_consent():
    service, _, http = radar_service()
    batch = await service.collect(radar_query("layer3"))
    assert not http.calls and not batch.items
    assert batch.attempts[0].status is CollectionStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_parent_control_denies_radar_and_its_specs():
    admission = Admission()
    admission.disabled.add(RADAR_PARENT)
    service, _, http = radar_service(allowed=True, admission=admission)
    batch = await service.collect(radar_query())
    assert not http.calls and not batch.items
    assert not set(RADAR_IDS) & {row.id for row in research_source_specs((RADAR_PARENT,))}
    disabled_factory = research_service(Mock(), FakeClock(NOW), disabled=(RADAR_PARENT,))
    assert not set(RADAR_IDS) & {row.id for row in disabled_factory._providers(radar_query())}


def test_fixed_series_and_distribution_routes_are_not_repeated_as_contrary_text_searches():
    service, _, _ = radar_service(allowed=True)
    excluded = {OnsCpihProvider.id, *RADAR_IDS}
    assert not excluded & {row.id for row in service._challenge_providers(radar_query())}
