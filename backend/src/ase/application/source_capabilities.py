"""Offline bundle resolution and prerequisite disclosure, without dispatch or secret access."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from ase.application.source_inventory import SourceRequirement
from ase.domain.source_capabilities import (
    CAPABILITY_POLICY_VERSION,
    CapabilityRef,
    SourceBundle,
    SourceCapability,
    UnavailableCapabilityGap,
)
from ase.domain.source_controls import source_control_keys


class CapabilityReadiness(StrEnum):
    PUBLIC_UNVERIFIED = "public_unverified"
    CONFIGURED_UNVERIFIED = "configured_unverified"
    REQUIREMENT_UNKNOWN = "requirement_unknown"
    REQUIREMENT_MISSING = "requirement_missing"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ResolvedCapability:
    capability: SourceCapability
    readiness: CapabilityReadiness


@dataclass(frozen=True, slots=True)
class BundleResolution:
    bundle_ids: tuple[str, ...]
    capabilities: tuple[ResolvedCapability, ...]
    gaps: tuple[UnavailableCapabilityGap, ...]
    policy_version: str = CAPABILITY_POLICY_VERSION

    @property
    def capability_count(self) -> int:
        return len(self.capabilities)

    @property
    def candidate_provider_ids(self) -> tuple[str, ...]:
        """Implemented, not administratively blocked, with declared prerequisites present.

        These are candidates only: current admission, provider support, query policy,
        permissions and operation budgets must still be checked before every dispatch.
        """
        return tuple(
            item.capability.id
            for item in self.capabilities
            if item.capability.provider_id is not None
            and item.readiness
            in (CapabilityReadiness.PUBLIC_UNVERIFIED, CapabilityReadiness.CONFIGURED_UNVERIFIED)
        )

    @property
    def known_origin_group_count(self) -> int:
        """Known catalogue origin groups across all references, not corroborating publishers."""
        return len({item.capability.origin_group for item in self.capabilities} - {None})

    @property
    def unknown_origin_capability_count(self) -> int:
        return sum(item.capability.origin_group is None for item in self.capabilities)


class SourceCapabilityRegistry:
    """Reviewed inventory with read-only mappings. Unknown references fail closed."""

    def __init__(
        self,
        capabilities: tuple[SourceCapability, ...],
        gaps: tuple[UnavailableCapabilityGap, ...],
        bundles: tuple[SourceBundle, ...],
    ) -> None:
        if len({row.id for row in capabilities}) != len(capabilities):
            raise ValueError("Duplicate capability ID")
        if len({row.id for row in gaps}) != len(gaps):
            raise ValueError("Duplicate gap ID")
        if len({row.id for row in bundles}) != len(bundles):
            raise ValueError("Duplicate bundle ID")
        self.capabilities = MappingProxyType({row.id: row for row in capabilities})
        self.gaps = MappingProxyType({row.id: row for row in gaps})
        self.bundles = MappingProxyType({row.id: row for row in bundles})
        for bundle in bundles:
            for ref in bundle.references:
                inventory = self.capabilities if isinstance(ref, CapabilityRef) else self.gaps
                if ref.id not in inventory:
                    raise ValueError("Bundle references an unknown capability or gap")

    def resolve(
        self,
        bundle_ids: tuple[str, ...],
        *,
        disabled: frozenset[str] = frozenset(),
        enabled: Mapping[str, bool] | None = None,
        requirements: Mapping[str, SourceRequirement] | None = None,
    ) -> BundleResolution:
        """Omitted enablement is static-only; supplied admission maps deny missing keys.

        Requirements contain presence metadata only. Presence never means tested access.
        Disabled parents suppress derivatives exactly as the current source guard does.
        """
        if len(bundle_ids) > 32 or any(key not in self.bundles for key in bundle_ids):
            raise ValueError("Unknown or excessive source bundle selection")
        ids = tuple(dict.fromkeys(bundle_ids))
        capabilities: dict[str, ResolvedCapability] = {}
        gaps: dict[str, UnavailableCapabilityGap] = {}
        for key in ids:
            for ref in self.bundles[key].references:
                if isinstance(ref, CapabilityRef):
                    capability = self.capabilities[ref.id]
                    capabilities[ref.id] = ResolvedCapability(
                        capability, _readiness(capability, disabled, enabled, requirements or {})
                    )
                else:
                    gaps[ref.id] = self.gaps[ref.id]
        return BundleResolution(ids, tuple(capabilities.values()), tuple(gaps.values()))


def _readiness(
    capability: SourceCapability,
    disabled: frozenset[str],
    enabled: Mapping[str, bool] | None,
    requirements: Mapping[str, SourceRequirement],
) -> CapabilityReadiness:
    keys = (*source_control_keys(capability.id), *capability.control_ids)
    if any(key in disabled for key in keys) or (
        enabled is not None
        and (
            not enabled.get(capability.id, False) or any(enabled.get(key) is False for key in keys)
        )
    ):
        return CapabilityReadiness.DISABLED
    required = tuple(item for item in capability.prerequisites if not item.optional)
    requirement = requirements.get(capability.id)
    if required or (requirement is not None and not requirement.optional):
        expected = {
            "runtime" if item.kind in {"retained_store", "private_input"} else item.kind.value
            for item in required
        }
        if (
            requirement is None
            or requirement.satisfied is None
            or (expected and requirement.kind not in expected)
        ):
            return CapabilityReadiness.REQUIREMENT_UNKNOWN
        if requirement.satisfied is False:
            return CapabilityReadiness.REQUIREMENT_MISSING
        return CapabilityReadiness.CONFIGURED_UNVERIFIED
    if requirement is not None and requirement.satisfied:
        return CapabilityReadiness.CONFIGURED_UNVERIFIED
    return CapabilityReadiness.PUBLIC_UNVERIFIED
