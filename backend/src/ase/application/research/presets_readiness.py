"""Explain scope, language and setup limits without claiming a provider was queried."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from ase.application.research.presets_schema import ResearchPreset
from ase.application.source_capabilities import CapabilityReadiness, SourceCapabilityRegistry
from ase.application.source_inventory import SourceRequirement
from ase.domain.research_capacity import MAX_SELECTED_SOURCES
from ase.domain.source_capabilities import (
    CapabilityScope,
    LanguageSupport,
    SourceCapability,
    UnavailableCapabilityGap,
)

READINESS_NOTE = (
    "Catalogue support and configuration presence are unverified. Candidate IDs are not "
    "dispatch authorisation or proof of scope, language, historical coverage or returned evidence. "
    "Current admission, exact provider support, disclosure choices and budgets apply at each run. "
    "The seven-day baseline is for initial activation; requested quarterly or annual intervals "
    "must retain their own historical coverage limits. No cadence is selected by a preset."
)


@dataclass(frozen=True, slots=True)
class PresetSourceReadiness:
    id: str
    name: str
    readiness: CapabilityReadiness
    candidate: bool
    scope_language_compatible: bool
    constraints: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PresetLanguageReceipt:
    language: str
    status: Literal["configured_route_unverified", "no_configured_route"]
    source_ids: tuple[str, ...]
    note: str = (
        "Configured query language is not detected source language. No translation or fallback "
        "has been performed; retain this language choice for explicit review if unsupported."
    )


@dataclass(frozen=True, slots=True)
class PresetBundleReadiness:
    id: str
    candidate_provider_ids: tuple[str, ...]
    gap_ids: tuple[str, ...]
    status: Literal["unverified_candidates", "declared_gaps", "unavailable"]


@dataclass(frozen=True, slots=True)
class PresetReadiness:
    policy_version: str
    source_bundles: tuple[PresetBundleReadiness, ...]
    sources: tuple[PresetSourceReadiness, ...]
    gaps: tuple[UnavailableCapabilityGap, ...]
    languages: tuple[PresetLanguageReceipt, ...]
    candidate_provider_ids: tuple[str, ...]
    source_selection_required: bool
    required_input_ids: tuple[str, ...]
    note: str = READINESS_NOTE


def _compatible(preset: ResearchPreset, capability: SourceCapability) -> bool:
    scopes = capability.support.scopes
    scope_ok = (
        CapabilityScope.AREA in scopes
        if preset.id == "area-custom"
        else CapabilityScope.TOPIC in scopes
        or bool(preset.country_isos and CapabilityScope.COUNTRY_CONTEXT in scopes)
    )
    support = capability.support
    language_ok = support.language_policy is LanguageSupport.NOT_FILTERED or bool(
        set(support.languages) & set(preset.suggested_languages)
    )
    return scope_ok and language_ok


def preset_readiness(
    preset: ResearchPreset,
    registry: SourceCapabilityRegistry,
    *,
    disabled: frozenset[str] = frozenset(),
    enabled: Mapping[str, bool] | None = None,
    requirements: Mapping[str, SourceRequirement] | None = None,
) -> PresetReadiness:
    resolved = registry.resolve(
        preset.source_bundles, disabled=disabled, enabled=enabled, requirements=requirements
    )
    candidates = frozenset(resolved.candidate_provider_ids)
    if preset.source_ids:
        candidates &= frozenset(preset.source_ids)
    sources = tuple(
        PresetSourceReadiness(
            row.capability.id,
            row.capability.name,
            row.readiness,
            row.capability.id in candidates and _compatible(preset, row.capability),
            _compatible(preset, row.capability),
            row.capability.support.constraints,
            row.capability.limitations,
        )
        for row in resolved.capabilities
    )
    selected = tuple(row.id for row in sources if row.candidate)
    gaps = {row.id: row for row in resolved.gaps}
    gaps.update((key, registry.gaps[key]) for key in preset.declared_gap_ids)
    bundles = []
    for bundle_id in preset.source_bundles:
        bundle = registry.resolve((bundle_id,))
        bundle_sources = {row.capability.id for row in bundle.capabilities}
        candidate_ids = tuple(key for key in selected if key in bundle_sources)
        status: Literal["unverified_candidates", "declared_gaps", "unavailable"] = (
            "unverified_candidates"
            if candidate_ids
            else "declared_gaps"
            if bundle.gaps
            else "unavailable"
        )
        bundles.append(
            PresetBundleReadiness(
                bundle_id, candidate_ids, tuple(row.id for row in bundle.gaps), status
            )
        )
    languages = []
    for language in preset.suggested_languages:
        ids = tuple(
            key
            for key in selected
            if registry.capabilities[key].support.language_policy is LanguageSupport.CONFIGURED
            and language in registry.capabilities[key].support.languages
        )
        languages.append(
            PresetLanguageReceipt(
                language, "configured_route_unverified" if ids else "no_configured_route", ids
            )
        )
    return PresetReadiness(
        resolved.policy_version,
        tuple(bundles),
        sources,
        tuple(gaps.values()),
        tuple(languages),
        selected,
        len(selected) > MAX_SELECTED_SOURCES,
        tuple(row.id for row in preset.required_inputs if row.required),
    )
