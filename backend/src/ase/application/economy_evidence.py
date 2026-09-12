"""Freeze six regional macro snapshots and three FX series, retaining observation periods."""

from dataclasses import replace
from datetime import datetime

from ase.domain.economy import EconomyRegion, EconomySeries, EconomySnapshot
from ase.domain.economy_catalogue import ANNUAL_PERIODS, INDICATORS, REGIONS
from ase.domain.events import (
    Category,
    Event,
    JsonScalar,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)


def economy_evidence(snapshot: EconomySnapshot, now: datetime) -> tuple[Event, ...]:
    records = []
    for region in snapshot.regions[:6]:
        item = _region_event(region, now)
        if item is not None:
            records.append(item)
    for series in snapshot.fx[:5]:
        item = _event(series, None, "Currency reference", now)
        if item is not None:
            records.append(item)
    return tuple(records[:11])


def _region_event(region: EconomyRegion, now: datetime) -> Event | None:
    observations = [
        event
        for series in region.series[: len(INDICATORS)]
        if (event := _event(series, region.id, region.name, now)) is not None
    ]
    if not observations:
        return None
    lines = []
    attributes: dict[str, JsonScalar] = {
        "record_kind": "economic_region_snapshot",
        "region": region.id,
    }
    for series in region.series[: len(INDICATORS)]:
        latest = next((p for p in reversed(series.points) if p.value is not None), None)
        attributes[f"{series.id}_observation_period"] = latest.date if latest else None
        attributes[f"{series.id}_source_updated_at"] = series.source_updated_at
        attributes[f"{series.id}_history"] = ";".join(
            f"{point.date}={point.value!r}" for point in series.points[-ANNUAL_PERIODS:]
        )
        lines.append(_observation_line(series))
    title = f"{region.name}: annual economic observations"
    first = observations[0]
    summary = (
        "Historical annual observations, not today's news. The collection timestamp is "
        "not the observation date. Years can differ; compare countries only in the same year. "
        "Debt covers central government only; GDP per capita is not income. "
        "Dollar GDP is nominal; capital formation is not financial investment. "
        "Figures rounded to 8 significant digits; missing years are not interpolated. "
        f"Source: World Bank. Retrieved {first.observed_at.isoformat()}; "
        f"provider update {region.series[0].source_updated_at or 'unknown'}. " + " ".join(lines)
    )
    code = next((code for key, _, code in REGIONS if key == region.id), None)
    if code is None:
        return None
    indicators = ";".join(indicator for _, _, indicator, _ in INDICATORS)
    url = (
        f"https://api.worldbank.org/v2/country/{code}/indicator/{indicators}"
        f"?source=2&format=json&date={now.year - ANNUAL_PERIODS}:{now.year - 1}"
        f"&per_page={len(INDICATORS) * ANNUAL_PERIODS}"
    )
    return replace(
        first,
        id=event_id("research-world-bank", f"economic-region:{region.id}"),
        title=title,
        summary=summary,
        url=url,
        attributes=freeze_attributes(attributes),
        content_hash=content_hash(
            title,
            *lines,
            *(str(value) for key, value in attributes.items() if key.endswith("_history")),
        ),
    )


def _observation_line(series: EconomySeries) -> str:
    available = [point for point in series.points if point.value is not None]
    if series.status == "unavailable" or not available:
        return f"{series.name}: unavailable."
    values = "; ".join(
        f"{point.date}={point.value:.8g}" for point in available[-2:] if point.value is not None
    )
    return f"{series.name}: {values} ({series.unit}; {series.status})."


def _event(series: EconomySeries, region: str | None, name: str, now: datetime) -> Event | None:
    if series.status == "unavailable":
        return None
    latest = next((point for point in reversed(series.points) if point.value is not None), None)
    if latest is None:
        return None
    source_id = "research-world-bank" if series.frequency == "annual" else "economic-ecb"
    title = f"{name}: {series.name}, observation {latest.date}"
    retrieved = series.updated_at.isoformat() if series.updated_at else "at an unknown time"
    earlier = next(
        (p for p in reversed(series.points) if p.value is not None and p.date < latest.date), None
    )
    comparison = (
        f"Previous observed value: {earlier.date}={earlier.value:.8g} {series.unit}. "
        if earlier is not None and series.frequency == "daily"
        else ""
    )
    summary = (
        f"{series.provider} published observation for {latest.date}: "
        f"{latest.value:g} {series.unit}. Retrieved {retrieved}. "
        f"Provider publication date: {series.source_updated_at or 'not supplied'}. "
        f"{comparison}Availability: {series.status}. {series.note} "
        "This is a captured series snapshot. Its collection timestamp is not the observation "
        "date or evidence of a development in the last 24 hours."
    )
    return Event(
        id=event_id(source_id, f"{region}:{series.id}:{latest.date}"),
        source_id=source_id,
        category=Category.ECONOMIC,
        subtype="economic_observation",
        title=title,
        summary=summary,
        url=series.source_url,
        # Neither annual observation years, provider calendar days nor retrieval
        # instants establish a reliable publication instant for these records.
        published_at=None,
        observed_at=series.updated_at or now,
        country_iso=region if region and region != "WORLD" else None,
        reliability=Reliability.F,
        grade_rationale="Source and underlying observation reliability have not been assessed.",
        tags=frozenset({"research_record", "economic_snapshot"}),
        attributes=freeze_attributes(
            {
                "record_kind": "economic_observation_snapshot",
                "observation_period": latest.date,
                "series_id": series.id,
                "value": latest.value,
                "unit": series.unit,
                "frequency": series.frequency,
                "snapshot_status": series.status,
                "source_updated_at": series.source_updated_at,
                "previous_observation_period": earlier.date if earlier else None,
                "previous_value": earlier.value if earlier else None,
            }
        ),
        content_hash=content_hash(title, str(latest.value), series.unit, comparison),
    )
