"""All approved R03 starters resolve honestly and copy into canonical editable definitions."""

import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from importlib.resources import files
from uuid import UUID

import pytest

from ase.api.schemas_research_briefs import ResearchBriefDraftIn
from ase.application.research.brief_codec import brief_from_dict, brief_to_dict
from ase.application.research.presets import (
    MAX_PRESET_BYTES,
    load_presets,
    parse_presets,
    pinned_preset,
    search_presets,
)
from ase.application.research.presets_definition import preset_definition
from ase.application.research.presets_readiness import preset_readiness
from ase.application.research.presets_schema import COMMON_SECTIONS, LENS_RULE
from ase.application.source_capabilities import CapabilityReadiness
from ase.application.source_inventory import SourceRequirement
from ase.container.research_capabilities import research_capability_registry
from ase.domain.errors import Conflict, NotFound
from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import BriefIdentity, BriefValidationError, LensId

EXPECTED = (
    "conflict-global",
    "conflict-russia-ukraine",
    "conflict-israel-gaza-west-bank",
    "conflict-iran-region",
    "conflict-taiwan-indopacific",
    "cyber-global",
    "cyber-uk-critical-sectors",
    "cyber-ransomware",
    "cyber-actor-watch",
    "cyber-technology-exploitation",
    "economy-global",
    "economy-uk",
    "economy-usa",
    "economy-china",
    "economy-russia",
    "economy-iran",
    "energy-security",
    "shipping-supply-chains",
    "disaster-humanitarian",
    "area-custom",
)
TRAPS = (
    "ordinary crime",
    "live positions",
    "contrary evidence",
    "intention assessments",
    "track gaps",
    "active scanning",
    "potential relevance",
    "leaked personal files",
    "ATT&CK",
    "similarity",
    "incompatible frequencies",
    "measured period",
    "trading recommendations",
    "distinct definitions",
    "inferred stability",
    "not interchangeable",
    "capacity",
    "receiver changes",
    "FIRMS",
    "precise incident",
)


@pytest.fixture
def registry():
    return research_capability_registry()


def test_all_approved_presets_are_searchable_schema_valid_and_have_quality_traps(registry):
    presets = load_presets(registry)
    assert tuple(row.id for row in presets) == EXPECTED
    for preset, trap in zip(presets, TRAPS, strict=True):
        assert search_presets(presets, query=preset.title) == (preset,)
        assert preset in search_presets(presets, group=preset.group)
        assert preset.default_depth is ResearchMode.DETAILED
        assert preset.reviewed_on.isoformat() == "2026-09-14"
        assert preset.baseline_days == 7
        assert len(preset.requirements) == 4
        assert trap in preset.quality_trap
        assert set(COMMON_SECTIONS) <= set(preset.sections)
        assert preset.lens_note == LENS_RULE
        ready = preset_readiness(preset, registry)
        assert all(
            bundle.candidate_provider_ids or bundle.gap_ids for bundle in ready.source_bundles
        )
        assert not any(key.startswith("gap.") for key in ready.candidate_provider_ids)
        assert "unverified" in ready.note
    assert not search_presets(presets, query="absent-subject")
    assert len(search_presets(presets, group="cyber")) == 5
    with pytest.raises(ValueError):
        search_presets(presets, query="x" * 121)


@pytest.mark.parametrize("preset_id", EXPECTED)
def test_every_definition_round_trips_without_owner_dates_or_source_fictions(registry, preset_id):
    preset = pinned_preset(load_presets(registry), preset_id, 1)
    ready = preset_readiness(preset, registry)
    definition = preset_definition(preset, ready)
    draft = ResearchBriefDraftIn.model_validate(definition)
    at = datetime(2026, 9, 14, tzinfo=UTC)
    identity = BriefIdentity(
        UUID(int=1),
        1,
        UUID(int=2),
        draft.title,
        at,
        at,
        preset_id=draft.preset_id,
        preset_version=draft.preset_version,
    )
    brief = draft.to_brief(identity)
    assert brief_from_dict(brief_to_dict(brief)) == brief
    assert "identity" not in definition
    assert brief.identity.preset_id == preset_id and brief.identity.preset_version == 1
    assert brief.collection.source_policy == "selected_only"
    assert set(brief.collection.source_ids or ()) <= set(ready.candidate_provider_ids)
    assert brief.collection.languages == preset.suggested_languages
    assert brief.output.language == "en"
    assert brief.observation.since is None and brief.observation.until is None
    assert brief.observation.lookback_hours == 168
    assert brief.lens.relevance_instructions.startswith(LENS_RULE)
    assert preset.scope_note in brief.lens.relevance_instructions


def test_basic_requires_explicit_reduction_and_lenses_survive(registry):
    preset = load_presets(registry)[0]
    readiness = preset_readiness(preset, registry)
    with pytest.raises(BriefValidationError, match="Reduce required"):
        preset_definition(preset, readiness, depth=ResearchMode.QUICK)
    selected = (preset.requirements[0].id, preset.requirements[3].id)
    for lens in LensId:
        copied = preset_definition(
            preset,
            readiness,
            depth=ResearchMode.QUICK,
            selected_requirement_ids=selected,
            lens=lens,
        )
        assert tuple(row["id"] for row in copied["question"]["requirements"]) == selected
        assert copied["lens"]["id"] == lens.value
        assert copied["output"]["depth"] == "quick"
    for selected in ((), ("unknown",), (preset.requirements[0].id,) * 2):
        with pytest.raises(BriefValidationError):
            preset_definition(preset, readiness, selected_requirement_ids=selected)
    narrowed = preset.model_copy(update={"lens_choices": (LensId.GENERAL,)})
    with pytest.raises(BriefValidationError):
        preset_definition(narrowed, readiness, lens=LensId.UK_POLICY)


def test_unavailable_sources_and_languages_are_visible_never_silently_substituted(registry):
    preset = pinned_preset(load_presets(registry), "conflict-iran-region", 1)
    selected = preset_readiness(preset, registry)
    assert {row.language for row in selected.languages} == {"en", "fa", "ar"}
    unavailable = preset_readiness(preset, registry, enabled={})
    assert not unavailable.candidate_provider_ids
    assert all(row.readiness is CapabilityReadiness.DISABLED for row in unavailable.sources)
    assert all(row.status == "no_configured_route" for row in unavailable.languages)
    definition = preset_definition(preset, unavailable)
    assert definition["collection"]["languages"] == ["en", "fa", "ar"]
    assert definition["collection"]["source_ids"] == []
    assert unavailable.gaps


def test_keys_and_disabled_parent_controls_remain_readiness_gaps(registry):
    preset = pinned_preset(load_presets(registry), "economy-uk", 1)
    ready = preset_readiness(preset, registry)
    keyed = next(
        row for row in ready.sources if row.readiness is CapabilityReadiness.REQUIREMENT_UNKNOWN
    )
    missing = SourceRequirement("api_key", False, "environment", None, "Missing setup")
    result = preset_readiness(
        preset, registry, disabled=frozenset({"google_news"}), requirements={keyed.id: missing}
    )
    source = next(row for row in result.sources if row.id == keyed.id)
    # Different prerequisite kinds stay unknown rather than being called configured.
    assert source.readiness in (
        CapabilityReadiness.REQUIREMENT_MISSING,
        CapabilityReadiness.REQUIREMENT_UNKNOWN,
    )
    assert not source.candidate
    assert all(not key.startswith("research_google_news_") for key in result.candidate_provider_ids)


def test_explicit_source_choices_and_oversized_pool_never_silently_widen(registry):
    preset = load_presets(registry)[0]
    readiness = preset_readiness(preset, registry)
    first = readiness.candidate_provider_ids[0]
    chosen = preset_definition(preset, readiness, selected_source_ids=(first,))
    assert chosen["collection"]["source_ids"] == [first]
    for sources in (("gap.original_passages",), ("invented",), (first, first)):
        with pytest.raises(BriefValidationError):
            preset_definition(preset, readiness, selected_source_ids=sources)
    oversized = replace(readiness, source_selection_required=True)
    assert preset_definition(preset, oversized)["collection"]["source_ids"] == []
    assert preset_definition(preset, oversized)["collection"]["source_policy"] == "selected_only"


def test_required_inputs_and_preset_revision_are_explicit(registry):
    presets = load_presets(registry)
    expected = {
        "cyber-uk-critical-sectors": ("sectors",),
        "cyber-actor-watch": ("actor",),
        "cyber-technology-exploitation": ("technologies",),
        "energy-security": ("region",),
        "shipping-supply-chains": ("routes",),
        "disaster-humanitarian": ("hazard_scope",),
        "area-custom": ("area", "question"),
    }
    for key, ids in expected.items():
        preset = pinned_preset(presets, key, 1)
        assert preset_readiness(preset, registry).required_input_ids == ids
    with pytest.raises(NotFound):
        pinned_preset(presets, "missing", 1)
    with pytest.raises(Conflict):
        pinned_preset(presets, presets[0].id, 2)
    original = preset_definition(presets[0], preset_readiness(presets[0], registry))
    edited = deepcopy(original)
    edited["question"]["main"] = "Edited question"
    assert original["question"]["main"] == presets[0].question


def test_catalogue_rejects_unknown_ids_excessive_bytes_and_invalid_shapes(registry):
    resource = files("ase.resources").joinpath("research_presets.json").read_bytes()
    for field, value in (
        ("source_bundles", ["INVENTED"]),
        ("source_ids", ["invented-provider"]),
        ("source_ids", ["research_import"]),
        ("declared_gap_ids", ["gap.invented"]),
        ("declared_gap_ids", ["fake-provider"]),
        ("version", "1"),
        ("lens_note", "Reach the preferred conclusion"),
        ("title", "<b>unsafe</b>"),
        ("sections", ["references"]),
        ("suggested_languages", ["en", "en"]),
    ):
        data = json.loads(resource)
        data["presets"][0][field] = value
        with pytest.raises(ValueError):
            parse_presets(json.dumps(data).encode(), registry)
    with pytest.raises(ValueError):
        parse_presets(b" " * (MAX_PRESET_BYTES + 1), registry)
    data = json.loads(resource)
    data["presets"][1]["id"] = data["presets"][0]["id"]
    with pytest.raises(ValueError):
        parse_presets(json.dumps(data).encode(), registry)
