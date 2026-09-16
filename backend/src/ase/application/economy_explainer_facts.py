"""The grounded fact pack: every figure, date and headline the explainer may use.

Nothing else reaches the model, and the mechanical checks later accept only numbers and
years that appear here. The fingerprint covers the facts, not the retrieval time, so a
refetch that changes nothing does not spend another model call.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from ase.application.economy_news import EconomyNewsItem
from ase.domain.economy import EconomyPoint, EconomySeries, EconomySnapshot, SeriesStatus
from ase.domain.economy_explainer import REGION_IDS

MAX_HEADLINES = 5
MAX_TITLE = 180
ChangeKind = Literal["percentage_point", "percentage_change", "none"]
SOURCE_LABELS = (
    "World Bank annual indicators",
    "European Central Bank euro reference rates",
    "Dated publisher economy headlines",
)


@dataclass(frozen=True, slots=True)
class IndicatorFact:
    id: str
    name: str
    unit: str
    status: SeriesStatus
    latest_year: str | None
    latest_value: float | None
    previous_year: str | None
    previous_value: float | None
    change: float | None
    change_kind: ChangeKind
    missing_years: tuple[str, ...]
    note: str


@dataclass(frozen=True, slots=True)
class HeadlineFact:
    title: str
    publisher: str
    published_on: str


@dataclass(frozen=True, slots=True)
class RegionFacts:
    id: str
    name: str
    indicators: tuple[IndicatorFact, ...]
    headlines: tuple[HeadlineFact, ...]
    available: int
    stale: int
    unavailable: int


@dataclass(frozen=True, slots=True)
class FxFact:
    id: str
    name: str
    unit: str
    status: SeriesStatus
    observed_on: str | None
    value: float | None
    previous_on: str | None
    previous_value: float | None
    note: str


@dataclass(frozen=True, slots=True)
class FactPack:
    fetched_at: datetime
    regions: tuple[RegionFacts, ...]
    fx: tuple[FxFact, ...]

    def region(self, key: str) -> RegionFacts | None:
        return next((item for item in self.regions if item.id == key), None)


def _observed(points: Sequence[EconomyPoint]) -> list[EconomyPoint]:
    return [point for point in points if point.value is not None]


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4) if abs(value) < 10_000 else round(value)


def _change(unit: str, latest: float | None, previous: float | None) -> tuple[float | None, str]:
    """Percentage-point differences for shares and rates; percentage change otherwise."""
    if latest is None or previous is None:
        return None, "none"
    if "%" in unit or "percent" in unit.lower():
        return round(latest - previous, 2), "percentage_point"
    if previous == 0:
        return None, "none"
    return round((latest - previous) / abs(previous) * 100, 2), "percentage_change"


def _gaps(series: EconomySeries) -> tuple[str, ...]:
    """Years inside the published range that carry no observation."""
    years = [point.date for point in series.points if point.value is None]
    return tuple(years[-6:])


def indicator_fact(series: EconomySeries) -> IndicatorFact:
    observed = _observed(series.points)
    latest = observed[-1] if observed else None
    previous = observed[-2] if len(observed) > 1 else None
    change, kind = _change(
        series.unit,
        latest.value if latest else None,
        previous.value if previous else None,
    )
    return IndicatorFact(
        id=series.id,
        name=series.name,
        unit=series.unit,
        status=series.status,
        latest_year=latest.date if latest else None,
        latest_value=_round(latest.value) if latest else None,
        previous_year=previous.date if previous else None,
        previous_value=_round(previous.value) if previous else None,
        change=change,
        change_kind=kind,  # type: ignore[arg-type]
        missing_years=_gaps(series),
        note=series.note[:400],
    )


def fx_fact(series: EconomySeries) -> FxFact:
    observed = _observed(series.points)
    latest = observed[-1] if observed else None
    previous = observed[-2] if len(observed) > 1 else None
    return FxFact(
        id=series.id,
        name=series.name,
        unit=series.unit,
        status=series.status,
        observed_on=latest.date if latest else None,
        value=_round(latest.value) if latest else None,
        previous_on=previous.date if previous else None,
        previous_value=_round(previous.value) if previous else None,
        note=series.note[:400],
    )


def _headlines(region: str, items: Sequence[EconomyNewsItem]) -> tuple[HeadlineFact, ...]:
    selected = [
        item
        for item in items
        if region == "WORLD" or region in item.region_codes
        # A worldwide headline list still names its publisher and date.
    ]
    return tuple(
        HeadlineFact(
            title=" ".join(item.title.split())[:MAX_TITLE],
            publisher=item.source_name,
            published_on=item.published_at.date().isoformat(),
        )
        for item in selected[:MAX_HEADLINES]
    )


def build_fact_pack(snapshot: EconomySnapshot, news: Sequence[EconomyNewsItem]) -> FactPack:
    regions = []
    for region in snapshot.regions:
        if region.id not in REGION_IDS:
            continue
        indicators = tuple(indicator_fact(series) for series in region.series)
        regions.append(
            RegionFacts(
                id=region.id,
                name=region.name,
                indicators=indicators,
                headlines=_headlines(region.id, news),
                available=sum(1 for item in indicators if item.status == "available"),
                stale=sum(1 for item in indicators if item.status == "stale"),
                unavailable=sum(1 for item in indicators if item.status == "unavailable"),
            )
        )
    order = {key: index for index, key in enumerate(REGION_IDS)}
    regions.sort(key=lambda item: order[item.id])
    rates = tuple(fx_fact(item) for item in snapshot.fx)
    return FactPack(snapshot.fetched_at, tuple(regions), rates)


def _indicator_document(fact: IndicatorFact) -> dict[str, Any]:
    return {
        "id": fact.id,
        "name": fact.name,
        "unit": fact.unit,
        "series_status": fact.status,
        "latest_year": fact.latest_year,
        "latest_value": fact.latest_value,
        "previous_year": fact.previous_year,
        "previous_value": fact.previous_value,
        "change": fact.change,
        "change_is": fact.change_kind,
        "years_without_an_observation": list(fact.missing_years),
        "note": fact.note,
    }


def fact_document(pack: FactPack) -> dict[str, Any]:
    """The canonical facts, without the retrieval time, as sent to the model and hashed."""
    return {
        "regions": [
            {
                "id": region.id,
                "name": region.name,
                "indicators_with_data": region.available,
                "indicators_from_an_older_cache": region.stale,
                "indicators_without_data": region.unavailable,
                "indicators": [_indicator_document(item) for item in region.indicators],
                "recent_headlines": [
                    {
                        "title": item.title,
                        "publisher": item.publisher,
                        "published_on": item.published_on,
                    }
                    for item in region.headlines
                ],
            }
            for region in pack.regions
        ],
        "exchange_reference_rates": [
            {
                "id": item.id,
                "name": item.name,
                "unit": item.unit,
                "series_status": item.status,
                "observed_on": item.observed_on,
                "value": item.value,
                "previous_observed_on": item.previous_on,
                "previous_value": item.previous_value,
                "note": item.note,
            }
            for item in pack.fx
        ],
    }


def fingerprint(pack: FactPack) -> str:
    document = json.dumps(
        fact_document(pack), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(document.encode("utf-8")).hexdigest()
