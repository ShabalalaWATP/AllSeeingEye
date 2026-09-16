"""Honest containment, an admin breakdown, and a baseline only where one is recorded."""

from datetime import UTC, datetime

import pytest

from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.ports.area_geography import EvidencePlacement
from ase.domain.area_context import (
    NO_BASELINE,
    AreaContext,
    BaselineComparison,
    ContainmentSplit,
    ScopeReceipt,
    context_from_dict,
    context_to_dict,
)
from ase.domain.canonical_provenance import canonical_snapshot
from ase.domain.research_records import ResearchReceipt
from test_asset_register_research import box

CAPTURED = datetime(2026, 9, 15, tzinfo=UTC)
KYIV_REGION = box(29.0, 49.5, 33.0, 51.5)


def placed(label, lon, lat, confidence):
    return EvidencePlacement(label, lon, lat, confidence)


def test_a_country_centroid_item_is_never_counted_as_inside_the_area():
    # The centroid of Ukraine falls well inside this box, but its confidence is country
    # level, so it must be reported as attached by country and never as located inside.
    result = PackagedAreaGeography().assemble(
        area=KYIV_REGION,
        country_isos=(),
        placements=(
            placed("E1", 30.52, 50.45, "exact"),
            placed("E2", 31.0, 50.5, "country"),
            placed("E3", 30.9, 50.6, "city"),
            placed("E4", None, None, "none"),
            placed("E5", 2.35, 48.85, "exact"),
        ),
    )
    assert result is not None
    split = result.containment
    assert (split.inside_exact, split.outside_exact) == (1, 1)
    assert (split.place_level, split.country_level, split.unlocated) == (1, 1, 1)
    assert split.total == 5
    text = split.describe()
    assert "1 precisely located inside the scope" in text
    assert "publisher's remit is never a location claim" in text


def test_the_scope_receipt_states_the_basis_and_its_limitation():
    result = PackagedAreaGeography().assemble(area=KYIV_REGION, country_isos=())
    assert result is not None
    assert result.scope.basis == "drawn_area"
    assert "collection choice" in result.scope.limitation


def test_the_breakdown_places_only_precisely_located_items_in_packaged_units():
    result = PackagedAreaGeography().assemble(
        area=KYIV_REGION,
        country_isos=(),
        placements=(
            placed("E1", 30.52, 50.45, "exact"),
            placed("E2", 30.60, 50.40, "exact"),
            placed("E3", 31.0, 50.5, "country"),
        ),
    )
    assert result is not None
    datasets = {row.dataset for row in result.breakdown}
    assert "geoBoundaries Ukraine oblasts" in datasets
    oblasts = next(row for row in result.breakdown if row.dataset.startswith("geoBoundaries"))
    assert sum(row.count for row in oblasts.rows) + oblasts.unassigned == 2
    assert "geoBoundaries" in oblasts.attribution
    assert "not an area of control" in oblasts.describe()


def test_an_unresolvable_scope_returns_nothing_rather_than_inventing_one():
    assert PackagedAreaGeography().assemble(area=None, country_isos=()) is None
    assert PackagedAreaGeography().assemble(area=None, country_isos=("MT",)) is None


def test_a_conflict_box_resolves_and_is_labelled_a_collection_box():
    result = PackagedAreaGeography().assemble(
        area=None,
        country_isos=(),
        box=(22.0, 44.0, 41.0, 52.5),
        box_label="ukraine",
        placements=(placed("E1", 30.52, 50.45, "exact"),),
    )
    assert result is not None and result.scope.basis == "conflict_box"
    assert "not a conflict boundary" in result.scope.limitation


def test_camera_coverage_is_read_only_when_it_is_asked_for():
    plain = PackagedAreaGeography().assemble(area=KYIV_REGION, country_isos=())
    asked = PackagedAreaGeography().assemble(area=KYIV_REGION, country_isos=(), cameras=True)
    assert plain is not None and asked is not None
    assert plain.registers == ()
    for entry in asked.registers:
        assert entry.asset_class == "cameras" and entry.count >= len(entry.listed)
        assert "no image, stream or current availability" in entry.attribution.lower()


def test_without_a_baseline_the_context_says_so_plainly():
    context = AreaContext(
        ScopeReceipt("drawn_area", "the drawn area", "A collection choice."),
        ContainmentSplit(inside_exact=3),
    )
    assert context.baselines == () and context.baseline_note == NO_BASELINE
    described = context.describe()
    assert "Is this normal? No recorded baseline covers this scope." in described
    assert "holds no baseline for an arbitrary outline" in described


def test_a_recorded_baseline_states_its_unit_and_its_limits():
    row = BaselineComparison(
        "military_aircraft", "UA", "Military aircraft over UA", 12, 4.0, 30, "B"
    )
    assert "12 now against a 30-day mean of 4.0 (3.0x the mean)" in row.describe()
    empty = BaselineComparison(
        "military_aircraft", "UA", "Military aircraft over UA", 1, None, 30, "B"
    )
    assert "no recorded mean for this key" in empty.describe()
    with pytest.raises(ValueError):
        BaselineComparison("k", "UA", "L", -1, 1.0, 30, "B")
    with pytest.raises(ValueError):
        BaselineComparison("k", "UA", "L", 1, 1.0, 0, "B")


def test_the_context_survives_a_serialisation_round_trip():
    result = PackagedAreaGeography().assemble(
        area=KYIV_REGION,
        country_isos=(),
        placements=(placed("E1", 30.52, 50.45, "exact"),),
        cameras=True,
    )
    assert result is not None
    context = AreaContext(
        result.scope,
        result.containment,
        result.breakdown,
        (BaselineComparison("military_aircraft", "UA", "Military over UA", 2, 1.5, 30, "B"),),
        "note",
        result.registers,
    )
    restored = context_from_dict(context_to_dict(context))
    assert restored == context
    with pytest.raises(ValueError):
        context_from_dict({"policy_version": "other"})
    assert context_to_dict(None) is None and context_from_dict(None) is None


def test_an_absent_area_context_leaves_historical_provenance_bytes_unchanged():
    receipt = ResearchReceipt("q", "quick", "general", ("en",), (), CAPTURED, CAPTURED, (), 0)
    assert "area_context" not in canonical_snapshot(receipt)
    present = ResearchReceipt(
        "q",
        "quick",
        "general",
        ("en",),
        (),
        CAPTURED,
        CAPTURED,
        (),
        0,
        area_context=AreaContext(
            ScopeReceipt("drawn_area", "the drawn area", "A collection choice."),
            ContainmentSplit(inside_exact=1),
        ),
    )
    assert "area_context" in canonical_snapshot(present)


def test_the_receipt_description_carries_the_context_only_when_it_exists():
    plain = ResearchReceipt("q", "quick", "general", ("en",), (), CAPTURED, CAPTURED, (), 0)
    assert "Area context" not in plain.describe()
    context = AreaContext(
        ScopeReceipt("country_outline", "the packaged outline of Ireland", "Coarse."),
        ContainmentSplit(inside_exact=2, country_level=9),
    )
    assert (
        "Area context"
        in plain.__class__(
            "q", "quick", "general", ("en",), (), CAPTURED, CAPTURED, (), 0, area_context=context
        ).describe()
    )
