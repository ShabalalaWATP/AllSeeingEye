"""Explicit metadata and optional behaviour survive either collection wrapper order."""

import asyncio
from dataclasses import FrozenInstanceError, replace

import pytest

from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.application.research.collection import ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.provider_capabilities import provider_capabilities
from ase.application.research.source_admission import ControlledResearchProvider
from ase.domain.registry_identifiers import registry_subject
from ase.domain.research import CollectionStatus
from ase.domain.research_plan import QueryVariant
from test_candidate_registry_limits import Admission
from test_candidate_registry_routing import candidate_query
from test_copernicus_research import AREA
from test_research_plan import QUERY, Provider


class DescribedProvider(Provider):
    capabilities = ProviderCapabilities(
        language="zh",
        query_language_aliases=("zh-cn",),
        supports_planned_terms=True,
        temporal_scope="Current observations only.",
        spatial_scope="Explicitly bounded area.",
        registry_namespaces=("sec_cik",),
    )

    def registry_subject(self, namespace, value):
        return registry_subject(namespace, value) if namespace == "sec_cik" else None

    def supports_area(self, query):
        return query.area is not None


def wrap(provider, admission, reverse):
    if reverse:
        return ControlledResearchProvider(PacedProvider(provider, RequestPacer()), admission)
    return PacedProvider(ControlledResearchProvider(provider, admission), RequestPacer())


@pytest.mark.parametrize("reverse", [False, True])
async def test_metadata_language_and_registry_routing_survive_wrappers(reverse):
    provider = DescribedProvider("source")
    wrapped = wrap(provider, Admission(True), reverse)
    assert provider_capabilities(wrapped) is provider.capabilities
    query = replace(
        QUERY, languages=("zh-cn",), query_variants=(QueryVariant("zh-CN", ("translated",)),)
    )
    batch = await ResearchCollector([wrapped]).collect(query)
    assert provider.queries[0].terms == ("translated",)
    task = batch.plan.tasks[0]
    assert task.language == "zh"
    assert task.temporal_scope == provider.capabilities.temporal_scope
    assert task.spatial_scope == provider.capabilities.spatial_scope
    assert task.planned_terms_supported
    exact = await ResearchCollector([wrapped]).collect(candidate_query("source"))
    assert exact.plan.tasks[1].supported
    assert provider.queries[-1].subject == "CIK:0000001234"
    assert exact.plan.tasks[0].registry_namespaces == ("sec_cik",)


@pytest.mark.parametrize("reverse", [False, True])
async def test_wrappers_keep_cancellation_and_source_disablement(reverse):
    provider = DescribedProvider("source", wait=True)
    admission = Admission(False)
    wrapped = wrap(provider, admission, reverse)
    disabled = await wrapped.collect(QUERY)
    assert disabled.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not provider.queries
    admission.value = True
    task = asyncio.create_task(wrapped.collect(QUERY))
    while not provider.queries:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_metadata_is_immutable_and_legacy_malformed_values_fail_conservatively():
    metadata = ProviderCapabilities()
    with pytest.raises(FrozenInstanceError):
        metadata.supports_planned_terms = True
    legacy = Provider("source")
    legacy.supports_planned_terms = "true"
    legacy.temporal_scope = " "
    legacy.spatial_scope = "x" * 1001
    legacy.query_language_aliases = None
    legacy.registry_namespaces = "sec_cik"
    assert provider_capabilities(legacy) == replace(metadata, language="en")


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("area_supported", [False, True])
async def test_optional_area_support_remains_explicit_through_wrappers(reverse, area_supported):
    provider = DescribedProvider("source") if area_supported else Provider("source")
    wrapped = wrap(provider, Admission(True), reverse)
    batch = await ResearchCollector([wrapped]).collect(replace(QUERY, area=AREA))
    assert batch.plan.tasks[0].spatial_supported is area_supported
    assert bool(provider.queries) is area_supported
