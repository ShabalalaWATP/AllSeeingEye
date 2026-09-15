"""Compose E00 readiness and reviewed allocation metadata without constructing providers."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ase.application.ports.source_controls import SourceAdmission
from ase.application.research.source_allocation_types import AllocationProfile
from ase.application.source_capabilities import ResolvedCapability, SourceCapabilityRegistry
from ase.application.source_inventory import SourceRequirement
from ase.container.research_allocation_profiles import (
    PROFILE_VERSION,
    REVIEW_DATE,
    research_allocation_profiles,
)
from ase.container.research_capabilities import research_capability_registry
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS
from ase.domain.source_capabilities import CapabilityRef, SourceBundle
from ase.domain.source_controls import source_control_keys


@dataclass(frozen=True, slots=True)
class ResearchAllocationContext:
    """A snapshot for pure ranking, never a substitute for current dispatch/release checks."""

    resolved: tuple[ResolvedCapability, ...]
    authorised_ids: frozenset[str]
    reviewed_profiles: Mapping[str, AllocationProfile]
    profile_version: str = PROFILE_VERSION
    profile_review_date: str = REVIEW_DATE


def _inventory(
    provider_ids: tuple[str, ...],
) -> tuple[SourceCapabilityRegistry, Mapping[str, AllocationProfile]]:
    registry = research_capability_registry()
    profiles = research_allocation_profiles()
    executable = {key for key, row in registry.capabilities.items() if row.provider_id is not None}
    if set(profiles) != executable:
        raise ValueError("Research providers changed without reviewed allocation profiles")
    if (
        not isinstance(provider_ids, tuple)
        or len(provider_ids) > MAX_COLLECTION_PROVIDERS
        or any(not isinstance(key, str) for key in provider_ids)
        or len(set(provider_ids)) != len(provider_ids)
        or not set(provider_ids) <= executable
    ):
        raise ValueError("Use bounded, unique, registered research provider IDs")
    return registry, profiles


def compose_research_allocation(
    provider_ids: tuple[str, ...],
    *,
    enabled: Mapping[str, bool],
    requirements: Mapping[str, SourceRequirement] | None = None,
    disabled: frozenset[str] = frozenset(),
) -> ResearchAllocationContext:
    """Use exact provider IDs and safe presence metadata from the current deployment.

    Missing/false admission denies a provider. Required settings omitted from
    requirements stay unknown; retained-area requires an explicit runtime presence
    record. Setting presence does not assert a working key or valid local dataset.
    No Settings instance, secret, dataset path, provider.supports call or query is read.
    Caller still supplies exact routed support, scope/date policy and requirements
    to allocate_sources, then rechecks admission at dispatch and result release.
    """
    registry, profiles = _inventory(provider_ids)
    ids = tuple(sorted(provider_ids))
    if not ids:
        return ResearchAllocationContext((), frozenset(), MappingProxyType({}))
    keys = {
        key
        for source_id in ids
        for key in (*source_control_keys(source_id), *registry.capabilities[source_id].control_ids)
    } | set(ids)
    # The wider source inventory may include other sources; none become provider IDs.
    admission = {key: enabled[key] is True for key in keys if key in enabled}
    needs = {key: value for key, value in (requirements or {}).items() if key in ids}
    if any(
        not isinstance(value, SourceRequirement)
        or (value.satisfied is not None and type(value.satisfied) is not bool)
        for value in needs.values()
    ):
        raise ValueError("Source requirements must contain safe typed presence metadata")
    # Reuse E00 readiness without requiring a public preset bundle for every provider.
    bundle = SourceBundle(
        "ALLOCATION", "Internal provider allocation", tuple(CapabilityRef(key) for key in ids)
    )
    selected = SourceCapabilityRegistry(
        tuple(registry.capabilities[key] for key in ids), (), (bundle,)
    ).resolve((bundle.id,), disabled=disabled, enabled=admission, requirements=needs)
    return ResearchAllocationContext(
        selected.capabilities,
        frozenset(selected.candidate_provider_ids),
        MappingProxyType({key: profiles[key] for key in ids}),
    )


async def load_research_allocation(
    provider_ids: tuple[str, ...],
    *,
    admission: SourceAdmission,
    requirements: Mapping[str, SourceRequirement] | None = None,
    disabled: frozenset[str] = frozenset(),
) -> ResearchAllocationContext:
    """Read current controls once, without holding a guard across ranking or collection.

    Failure propagates before any dispatch. This snapshot can become stale, so the
    existing ControlledResearchProvider admission and release checks must remain.
    """
    registry, _ = _inventory(provider_ids)
    keys = tuple(
        sorted(
            {
                key
                for source_id in provider_ids
                for key in (
                    source_id,
                    *source_control_keys(source_id),
                    *registry.capabilities[source_id].control_ids,
                )
            }
        )
    )
    enabled = await admission.enabled_many(keys) if keys else {}
    return compose_research_allocation(
        provider_ids, enabled=enabled, requirements=requirements, disabled=disabled
    )
