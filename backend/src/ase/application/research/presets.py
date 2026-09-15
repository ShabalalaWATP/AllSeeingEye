"""Load and search reviewed presets, checking all references against the E00 registry."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from ase.application.research.presets_schema import PresetGroup, PresetResource, ResearchPreset
from ase.application.source_capabilities import SourceCapabilityRegistry
from ase.domain.errors import Conflict, NotFound

MAX_PRESET_BYTES = 256 * 1024


def parse_presets(payload: bytes, registry: SourceCapabilityRegistry) -> tuple[ResearchPreset, ...]:
    if len(payload) > MAX_PRESET_BYTES:
        raise ValueError("Preset catalogue exceeds its byte limit")
    presets = PresetResource.model_validate_json(payload).presets
    for preset in presets:
        registry.resolve((*preset.source_bundles, *preset.optional_bundles))
        if any(key not in registry.capabilities for key in preset.source_ids):
            raise ValueError("Preset references an unknown source capability")
        required = registry.resolve(preset.source_bundles)
        if not set(preset.source_ids) <= {row.capability.id for row in required.capabilities}:
            raise ValueError("Preset source choices must belong to its required bundles")
        if any(key not in registry.gaps for key in preset.declared_gap_ids):
            raise ValueError("Preset references an unknown declared coverage gap")
    return presets


@lru_cache(maxsize=1)
def _resource() -> bytes:
    with files("ase.resources").joinpath("research_presets.json").open("rb") as handle:
        return handle.read(MAX_PRESET_BYTES + 1)


def load_presets(registry: SourceCapabilityRegistry) -> tuple[ResearchPreset, ...]:
    return parse_presets(_resource(), registry)


def search_presets(
    presets: tuple[ResearchPreset, ...], *, query: str = "", group: PresetGroup | None = None
) -> tuple[ResearchPreset, ...]:
    if len(query) > 120:
        raise ValueError("Preset search is limited to 120 characters")
    terms = query.casefold().split()
    return tuple(
        preset
        for preset in presets
        if (group is None or preset.group == group)
        and all(
            term
            in " ".join(
                (preset.id, preset.title, preset.purpose, *preset.keywords, preset.question)
            ).casefold()
            for term in terms
        )
    )


def pinned_preset(
    presets: tuple[ResearchPreset, ...], preset_id: str, version: int
) -> ResearchPreset:
    preset = next((row for row in presets if row.id == preset_id), None)
    if preset is None:
        raise NotFound("Research preset not found.")
    if preset.version != version:
        raise Conflict("The preset version changed. Review it before adopting the update.")
    return preset
