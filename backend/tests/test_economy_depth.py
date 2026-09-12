"""Deeper economic snapshots retain dated context without widening ordinary feed prompts."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.economy_evidence import economy_evidence
from ase.application.reports.prompts import evidence_block
from ase.domain.economy import EconomyPoint, EconomySnapshot
from ase.domain.economy_catalogue import INDICATORS, empty_fx
from ase.domain.events import MAX_ATTRIBUTES, MAX_SUMMARY
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import EvidenceAttribute
from test_economy_data import NOW, parse_world_bank, wb_payload, wb_row


def frozen(event):
    return EvidenceItem.from_event(
        "E1", event, NOW, source_name="World Bank", independence_key="World Bank"
    )


def snapshot_events(*rows):
    return economy_evidence(
        EconomySnapshot(
            NOW, NOW + timedelta(hours=1), parse_world_bank(wb_payload(*rows), NOW), empty_fx()
        ),
        NOW,
    )


def test_full_expanded_batch_preserves_observed_values_and_specific_series_scope():
    rows = [
        wb_row(indicator={"id": code}, date="2024", value=value)
        for (_, _, code, _), value in zip(INDICATORS, range(1, 13), strict=True)
    ]
    region = parse_world_bank(wb_payload(*rows), NOW)[1]
    by_id = {series.id: series for series in region.series}
    assert len(by_id) == 12
    assert all(series.points[-2].value == index for index, series in enumerate(region.series, 1))
    assert all(series.points[-1].value is None for series in region.series)
    assert by_id["gdp_per_capita"].unit == "Current US dollars"
    assert by_id["population"].unit == "People"
    assert by_id["government_debt"].name == "Central government debt"
    assert "not consolidated general-government debt" in by_id["government_debt"].note
    assert "not purchases of financial investments" in by_id["investment"].note
    assert "not the trade balance alone" in by_id["current_account"].note
    assert "not all industry" in by_id["manufacturing"].note


def test_twelve_series_with_two_observations_fit_frozen_and_prompt_budgets():
    rows = [
        wb_row(indicator={"id": code}, date=str(year), value=-9.876543212345678e-123)
        for _, _, code, _ in INDICATORS
        for year in range(2014, 2026)
    ]
    event = snapshot_events(*rows)[0]
    assert len(event.summary) <= MAX_SUMMARY
    assert len(event.attributes) <= MAX_ATTRIBUTES
    assert len(frozen(event).attributes) == len(event.attributes) == 38
    prompt = evidence_block(frozen(event))
    for identifier, label, _, _ in INDICATORS:
        assert label in prompt
        assert event.attributes[f"{identifier}_observation_period"] == "2025"
        assert event.attributes[f"{identifier}_source_updated_at"] == "2026-07-13"
        history = event.attributes[f"{identifier}_history"]
        assert "2014=-9.876543212345678e-123" in history
        assert "2025=-9.876543212345678e-123" in history
    assert "2024=-9.8765432e-123; 2025=-9.8765432e-123" in prompt
    assert "Debt covers central government only" in prompt
    assert event.summary in prompt


def test_annual_evidence_does_not_turn_nonadjacent_observations_into_annual_growth():
    event = snapshot_events(
        wb_row(date="2023", value=100),
        wb_row(date="2024", value=None),
        wb_row(date="2025", value=125),
    )[0]
    assert "GDP: 2023=100; 2025=125" in event.summary
    assert "missing years are not interpolated" in event.summary
    assert "2024=None" in event.attributes["gdp_history"]
    assert event.published_at is None
    assert "2024=" not in event.summary
    assert "25%" not in event.summary


def test_older_revision_changes_frozen_snapshot_hash_even_when_latest_values_are_identical():
    observations = (wb_row(date="2024", value=110), wb_row(date="2025", value=125))
    first = snapshot_events(wb_row(date="2023", value=100), *observations)[0]
    revised = snapshot_events(wb_row(date="2023", value=101), *observations)[0]
    assert first.summary == revised.summary
    assert first.content_hash != revised.content_hash
    assert first.attributes["gdp_history"] != revised.attributes["gdp_history"]


def test_fx_context_preserves_previous_observation_for_dated_change_analysis():
    series = replace(
        empty_fx()[0],
        status="available",
        updated_at=NOW,
        points=(
            EconomyPoint("2026-09-09", 0.84),
            EconomyPoint("2026-09-10", None),
            EconomyPoint("2026-09-11", 0.85),
        ),
    )
    event = economy_evidence(EconomySnapshot(NOW, NOW + timedelta(hours=1), (), (series,)), NOW)[0]
    assert "Previous observed value: 2026-09-09=0.84 GBP per EUR" in event.summary
    assert event.attributes["previous_observation_period"] == "2026-09-09"
    assert event.attributes["previous_value"] == 0.84
    assert "2026-09-10" not in event.summary


@pytest.mark.parametrize(
    ("source_id", "category", "marker"),
    [
        ("publisher", "economic", "economic_region_snapshot"),
        ("research-world-bank", "news", "economic_region_snapshot"),
        ("research-world-bank", "economic", "untrusted_snapshot"),
        ("research-world-bank", "economic", "economic_observation_snapshot"),
        ("economic-ecb", "economic", "economic_region_snapshot"),
    ],
)
def test_economic_prompt_budget_cannot_be_selected_by_unrelated_source_or_marker(
    source_id, category, marker
):
    item = replace(
        frozen(snapshot_events(wb_row())[0]),
        source_id=source_id,
        category=category,
        attributes=(EvidenceAttribute("record_kind", marker),),
        summary="x" * 700 + "DETAIL_BEYOND_600",
    )
    assert "DETAIL_BEYOND_600" not in evidence_block(item)
    assert "x" * 600 not in evidence_block(item)


@pytest.mark.parametrize(
    ("source_id", "marker"),
    [
        ("research-world-bank", "economic_region_snapshot"),
        ("economic-ecb", "economic_observation_snapshot"),
    ],
)
def test_verified_snapshot_prompt_expansion_remains_bounded(source_id, marker):
    item = replace(
        frozen(snapshot_events(wb_row())[0]),
        source_id=source_id,
        attributes=(EvidenceAttribute("record_kind", marker),),
        summary="x" * 700 + "RETAINED" + "x" * 1400 + "REJECTED",
    )
    prompt = evidence_block(item)
    assert "RETAINED" in prompt and "REJECTED" not in prompt
