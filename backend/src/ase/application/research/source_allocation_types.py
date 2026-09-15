"""Reviewed source metadata, immutable E01 allocation receipts and versioned ceilings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType

from ase.domain.research import ResearchMode
from ase.domain.source_capabilities import DateSupport

POLICY_VERSION = "ase-source-allocation-v2"
WEIGHTS = MappingProxyType(
    {
        "required": 12,
        "optional": 3,
        "subject": 12,
        "question": 8,
        "operator_terms": 8,
        "geography": 12,
        "language": 6,
        "primary": 12,
        "same_origin_penalty": 18,
    }
)
# Total operations, challenge operations, initial/challenge seconds and retained items.
DEPTH_CAPS = MappingProxyType(
    {
        ResearchMode.QUICK: (6, 0, 45, 0, 200, 0),
        ResearchMode.DETAILED: (24, 4, 135, 45, 792, 8),
        ResearchMode.ADVANCED: (32, 6, 180, 60, 988, 12),
    }
)
RESERVATION_QUOTAS = MappingProxyType(
    {
        ResearchMode.QUICK: (1, 0),
        ResearchMode.DETAILED: (2, 1),
        ResearchMode.ADVANCED: (3, 2),
    }
)


@dataclass(frozen=True, slots=True)
class AllocationProfile:
    """Reviewed source-purpose metadata, never a model's unsupported attribution.

    Countries describe useful coverage, not reliability or incident coordinates.
    Primary content requires provenance review AND a non-discovery data capability.
    Local-language means a reviewed publisher route, not a Google edition alone.
    """

    terms: tuple[str, ...]
    review_note: str
    countries: tuple[str, ...] = ()
    primary_content: bool = False
    local_language: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.terms, tuple)
            or len(self.terms) > 24
            or any(not isinstance(x, str) or not x.strip() or len(x) > 80 for x in self.terms)
            or not isinstance(self.review_note, str)
            or not 1 <= len(self.review_note) <= 200
            or not isinstance(self.countries, tuple)
            or len(self.countries) > 32
            or any(
                not isinstance(x, str) or not re.fullmatch(r"[A-Z]{2}", x) for x in self.countries
            )
            or type(self.primary_content) is not bool
            or type(self.local_language) is not bool
        ):
            raise ValueError("Use bounded, reviewed source allocation metadata")


@dataclass(frozen=True, slots=True)
class PhaseAllocation:
    initial_operations: int
    challenge_operations: int
    initial_seconds: int
    challenge_seconds: int
    initial_items: int
    challenge_items: int


@dataclass(frozen=True, slots=True)
class SourceAllocationReceipt:
    source_id: str
    disposition: str
    reasons: tuple[str, ...]
    requirement_ids: tuple[str, ...] = ()
    score_components: tuple[tuple[str, int], ...] = ()
    declared_languages: tuple[str, ...] = ()
    declared_dates: tuple[DateSupport, ...] = ()


@dataclass(frozen=True, slots=True)
class ReservationReceipt:
    kind: str
    requested: int
    planned: int
    reason: str


@dataclass(frozen=True, slots=True)
class SourceAllocation:
    provider_ids: tuple[str, ...]
    receipts: tuple[SourceAllocationReceipt, ...]
    reservations: tuple[ReservationReceipt, ...]
    requirement_sources: tuple[tuple[str, tuple[str, ...]], ...]
    phases: PhaseAllocation
    catalogue_capabilities: int
    eligible_operations: int
    known_origin_groups: int
    unknown_origin_operations: int
    policy_version: str = POLICY_VERSION
    attempted_operations: int = 0
    transport_requests: int = 0
    returned_items: int = 0
    retained_items: int = 0
    selected_items: int = 0
    retrieved_at: None = None
    max_public_concurrency: int = 2
    max_per_host_concurrency: int = 1
    coverage_note: str = (
        "Planned operations only. No source was queried and no evidence coverage or independence "
        "is established. Requirement IDs denote proposed coverage. Missing reservations are "
        "reallocated within the initial cap; challenge operations, time and items stay reserved. "
        "Origin groups are catalogue estimates, not corroborating publishers."
    )

    @property
    def planned_operations(self) -> int:
        return len(self.provider_ids)
