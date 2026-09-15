"""Offline E00 acceptance: real IDs, honest gaps, safe readiness and distinct origin counts."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from ase.application.source_capabilities import CapabilityReadiness, SourceCapabilityRegistry
from ase.application.source_inventory import SourceRequirement
from ase.container import research_capabilities
from ase.container.research_capabilities import research_capability_registry
from ase.container.research_sources import research_source_specs
from ase.domain.source_capabilities import (
    CapabilityRef,
    ContentCapability,
    ExecutionRoute,
    GapRef,
    SourceBundle,
    SourceCapability,
    UnavailableCapabilityGap,
)
from ase.infrastructure.settings import Settings


@pytest.fixture
def contract() -> dict[str, Any]:
    path = Path(__file__).parent / "fixtures" / "research_capabilities_e00.json"
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@pytest.fixture
def registry() -> SourceCapabilityRegistry:
    return research_capability_registry()


def selected_registry(*rows: SourceCapability) -> SourceCapabilityRegistry:
    return SourceCapabilityRegistry(
        rows,
        (),
        (SourceBundle("TEST", "Selected routes", tuple(CapabilityRef(r.id) for r in rows)),),
    )


def requirement(
    present: bool | None, *, kind: str = "api_key", optional: bool = False
) -> SourceRequirement:
    return SourceRequirement(kind, present, "unknown", None, "Presence only", optional)  # type: ignore[arg-type]


def test_factory_never_constructs_settings_or_makes_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("An offline capability inventory must not access runtime configuration/network")

    monkeypatch.setattr(Settings, "__init__", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden)
    registry = research_capability_registry()
    assert len(registry.capabilities) > 100
    assert registry.resolve(("NEWS",)).candidate_provider_ids


def test_registry_covers_catalogue_without_turning_private_routes_into_providers(
    registry: SourceCapabilityRegistry,
) -> None:
    assert set(registry.capabilities) == {spec.id for spec in research_source_specs()}
    separate = {row.id for row in registry.capabilities.values() if row.provider_id is None}
    assert separate == {"research_import", "research_media", "research-web-search"}
    for key in separate:
        resolved = selected_registry(registry.capabilities[key]).resolve(
            ("TEST",), requirements={key: requirement(True, kind="runtime")}
        )
        assert resolved.candidate_provider_ids == ()
    assert registry.capabilities["research-web-search"].route is ExecutionRoute.FRESH_WEB
    assert "cisa_kev" not in registry.capabilities
    assert "mitre_attack" not in registry.capabilities
    assert "cloudflare_radar_outages" not in registry.capabilities


def test_new_catalogue_entry_needs_a_reviewed_executable_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = research_source_specs()
    monkeypatch.setattr(
        research_capabilities,
        "research_source_specs",
        lambda: (*specs, replace(specs[0], id="research-not-implemented")),
    )
    with pytest.raises(ValueError, match="without a reviewed capability profile"):
        research_capability_registry()


def test_all_bundles_resolve_to_reviewed_capabilities_or_explicit_gaps(
    registry: SourceCapabilityRegistry, contract: dict[str, Any]
) -> None:
    assert list(registry.bundles) == contract["bundle_ids"]
    all_bundles = registry.resolve(tuple(registry.bundles))
    assert all_bundles.policy_version == contract["policy_version"]
    assert (
        len({row.capability.id for row in all_bundles.capabilities}) == all_bundles.capability_count
    )
    assert len({gap.id for gap in all_bundles.gaps}) == len(all_bundles.gaps)
    assert not set(all_bundles.candidate_provider_ids).intersection(registry.gaps)
    assert not any(row.startswith("gap.") for row in all_bundles.candidate_provider_ids)
    for example in contract["bundle_examples"]:
        bundle = registry.resolve((example["bundle"],))
        assert example["provider"] in {row.capability.id for row in bundle.capabilities}
        assert example["gap"] in {row.id for row in bundle.gaps}
    assert registry.resolve(("CTI", "CTI")) == registry.resolve(("CTI",))


def test_scope_language_and_time_support_discloses_current_snapshot_limits(
    registry: SourceCapabilityRegistry, contract: dict[str, Any]
) -> None:
    for example in contract["support_examples"]:
        capability = registry.capabilities[example["id"]]
        assert example["scope"] in capability.support.scopes
        assert example["date"] in capability.support.dates
        if example["language"] is not None:
            assert example["language"] in capability.support.languages
        assert capability.support.constraints
        assert capability.limitations
    chinese = registry.capabilities["research_regional_cdt_zh"]
    assert set(chinese.support.languages) == {"zh", "zh-cn", "zh-hans"}
    assert registry.capabilities["research_publisher_cyber_ncsc_news"].content is (
        ContentCapability.DISCOVERY
    )


def test_editions_and_subject_variants_do_not_inflate_origin_groups(
    registry: SourceCapabilityRegistry, contract: dict[str, Any]
) -> None:
    for ids in contract["same_origin_pairs"]:
        selection = selected_registry(*(registry.capabilities[key] for key in ids)).resolve(
            ("TEST",)
        )
        assert selection.capability_count == 2
        assert selection.known_origin_group_count == 1
        assert selection.unknown_origin_capability_count == 0
    scholarly = registry.resolve(("SCHOLARLY",))
    assert scholarly.capability_count == 2
    assert scholarly.known_origin_group_count == 0
    assert scholarly.unknown_origin_capability_count == 2
    editions = selected_registry(
        *(row for row in registry.capabilities.values() if row.family == "news_discovery")
    ).resolve(("TEST",))
    assert editions.capability_count > 10
    assert editions.known_origin_group_count == 0
    assert editions.unknown_origin_capability_count == editions.capability_count


@pytest.mark.parametrize(
    ("source_id", "disabled_id"),
    [
        ("research_publisher_bbc_world", "bbc_world"),
        ("research_google_news_en", "google_news"),
        ("research_google_news_fr", "google_news_watchlists"),
        ("research-usgs-area", "usgs_earthquakes"),
        ("research-ooni-aggregate", "research-ooni-aggregate"),
    ],
)
def test_disabled_parents_keep_visible_exclusions_but_are_never_candidates(
    registry: SourceCapabilityRegistry, source_id: str, disabled_id: str
) -> None:
    selected = selected_registry(registry.capabilities[source_id])
    result = selected.resolve(("TEST",), disabled=frozenset({disabled_id}))
    assert result.capability_count == 1
    assert result.capabilities[0].readiness is CapabilityReadiness.DISABLED
    assert result.candidate_provider_ids == ()


@pytest.mark.parametrize(
    "enabled",
    [
        {},
        {"research_publisher_bbc_world": False},
        {"research_publisher_bbc_world": True, "bbc_world": False},
    ],
)
def test_supplied_admission_mapping_fails_closed(
    registry: SourceCapabilityRegistry, enabled: dict[str, bool]
) -> None:
    selected = selected_registry(registry.capabilities["research_publisher_bbc_world"])
    result = selected.resolve(("TEST",), enabled=enabled)
    assert result.capabilities[0].readiness is CapabilityReadiness.DISABLED
    assert result.candidate_provider_ids == ()


@pytest.mark.parametrize(
    ("present", "state"),
    [
        (None, CapabilityReadiness.REQUIREMENT_UNKNOWN),
        (False, CapabilityReadiness.REQUIREMENT_MISSING),
        (True, CapabilityReadiness.CONFIGURED_UNVERIFIED),
    ],
)
def test_credentials_are_presence_only_never_connected(
    registry: SourceCapabilityRegistry, present: bool | None, state: CapabilityReadiness
) -> None:
    source_id = "research-companies-house"
    selected = selected_registry(registry.capabilities[source_id])
    result = selected.resolve(("TEST",), requirements={source_id: requirement(present)})
    assert result.capabilities[0].readiness is state
    assert bool(result.candidate_provider_ids) is (present is True)
    assert selected.resolve(("TEST",)).capabilities[0].readiness is (
        CapabilityReadiness.REQUIREMENT_UNKNOWN
    )


def test_acknowledgement_snapshots_and_cache_require_their_own_prerequisite(
    registry: SourceCapabilityRegistry,
) -> None:
    for source_id, kind in (
        ("research-ooni-aggregate", "acknowledgement"),
        ("research-designations-uksl", "snapshot"),
        ("research-aiddata-projects", "catalogue"),
        ("research-retained-area-feeds", "runtime"),
    ):
        selected = selected_registry(registry.capabilities[source_id])
        wrong = selected.resolve(("TEST",), requirements={source_id: requirement(True)})
        assert not wrong.candidate_provider_ids
        ready = selected.resolve(("TEST",), requirements={source_id: requirement(True, kind=kind)})
        assert ready.candidate_provider_ids == (source_id,)


def test_optional_key_does_not_block_public_route_and_runtime_gates_are_respected(
    registry: SourceCapabilityRegistry,
) -> None:
    source_id = "research-openalex"
    selected = selected_registry(registry.capabilities[source_id])
    public = selected.resolve(
        ("TEST",), requirements={source_id: requirement(False, optional=True)}
    )
    assert public.capabilities[0].readiness is CapabilityReadiness.PUBLIC_UNVERIFIED
    configured = selected.resolve(
        ("TEST",), requirements={source_id: requirement(True, optional=True)}
    )
    assert configured.capabilities[0].readiness is CapabilityReadiness.CONFIGURED_UNVERIFIED
    # A new mandatory runtime gate must not be ignored merely because the catalogue is public.
    blocked = selected.resolve(("TEST",), requirements={source_id: requirement(False)})
    assert not blocked.candidate_provider_ids


@pytest.mark.parametrize("ids", [("UNKNOWN",), ("gap.cti_kev",), ("NEWS",) * 33])
def test_unknown_bundle_selection_is_rejected(
    registry: SourceCapabilityRegistry, ids: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError, match="Unknown or excessive"):
        registry.resolve(ids)


def test_invalid_reference_types_and_unknown_ids_are_rejected(
    registry: SourceCapabilityRegistry,
) -> None:
    capability = registry.capabilities["research-openalex"]
    with pytest.raises(ValueError, match="gap reference"):
        CapabilityRef("gap.cti_kev")
    with pytest.raises(ValueError, match="gap namespace"):
        GapRef("research-openalex")
    with pytest.raises(ValueError, match="declared gap"):
        replace(capability, id="gap.fake")
    for ref in (CapabilityRef("research-unknown"), GapRef("gap.unknown")):
        with pytest.raises(ValueError, match="unknown capability or gap"):
            SourceCapabilityRegistry((capability,), (), (SourceBundle("TEST", "Test", (ref,)),))
    with pytest.raises(ValueError, match="unique"):
        SourceBundle("TEST", "Test", (CapabilityRef(capability.id), CapabilityRef(capability.id)))
    with pytest.raises(ValueError, match="one to 256"):
        SourceBundle("TEST", "Test", ())
    with pytest.raises(ValueError, match="typed references"):
        SourceBundle("TEST", "Test", ("research-openalex",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="name and reason"):
        UnavailableCapabilityGap("gap.empty", "", "")
    with pytest.raises(ValueError, match="names, support"):
        replace(capability, name="")


def test_duplicate_inventory_ids_and_mutation_are_rejected(
    registry: SourceCapabilityRegistry,
) -> None:
    capability = registry.capabilities["research-openalex"]
    gap = registry.gaps["gap.cti_kev"]
    bundle = SourceBundle("TEST", "Test", (CapabilityRef(capability.id),))
    cases = (
        ((capability, capability), (), (bundle,)),
        ((capability,), (gap, gap), (bundle,)),
        ((capability,), (), (bundle, bundle)),
    )
    for capabilities, gaps, bundles in cases:
        with pytest.raises(ValueError, match="Duplicate"):
            SourceCapabilityRegistry(capabilities, gaps, bundles)
    with pytest.raises(TypeError):
        registry.capabilities[capability.id] = capability  # type: ignore[index]
