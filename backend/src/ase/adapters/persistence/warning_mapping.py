"""Mapping durable warning rows to scoped domain records."""

from ase.adapters.persistence.models import AlertRow, IndicatorRow
from ase.domain.events import BoundingBox, Category
from ase.domain.warning import Alert, Indicator


def _indicator_from_row(row: IndicatorRow) -> Indicator:
    bbox = None
    edges = (row.west, row.south, row.east, row.north)
    if all(edge is not None for edge in edges):
        bbox = BoundingBox(west=edges[0], south=edges[1], east=edges[2], north=edges[3])  # type: ignore[arg-type]
    return Indicator(
        id=row.id,
        name=row.name,
        description=row.description,
        plan_id=row.plan_id,
        countries=tuple(str(code) for code in row.countries),
        bbox=bbox,
        categories=tuple(Category(str(value)) for value in row.categories),
        keywords=tuple(str(word) for word in row.keywords),
        threshold=row.threshold,
        window_minutes=row.window_minutes,
        cooldown_minutes=row.cooldown_minutes,
        severity_floor=row.severity_floor,
        report_template=row.report_template,
        enabled=row.enabled,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        team_id=row.team_id,
    )


def _fill_indicator(row: IndicatorRow, indicator: Indicator) -> None:
    row.name = indicator.name
    row.description = indicator.description
    row.plan_id = indicator.plan_id
    row.countries = list(indicator.countries)
    row.west = indicator.bbox.west if indicator.bbox else None
    row.south = indicator.bbox.south if indicator.bbox else None
    row.east = indicator.bbox.east if indicator.bbox else None
    row.north = indicator.bbox.north if indicator.bbox else None
    row.categories = [category.value for category in indicator.categories]
    row.keywords = list(indicator.keywords)
    row.threshold = indicator.threshold
    row.window_minutes = indicator.window_minutes
    row.cooldown_minutes = indicator.cooldown_minutes
    row.severity_floor = indicator.severity_floor
    row.report_template = indicator.report_template
    row.enabled = indicator.enabled
    row.created_by = indicator.created_by
    row.created_at = indicator.created_at
    row.updated_at = indicator.updated_at
    row.team_id = indicator.team_id


def _alert_from_row(row: AlertRow) -> Alert:
    return Alert(
        id=row.id,
        indicator_id=row.indicator_id,
        schedule_id=row.schedule_id,
        annotation_monitor_id=row.annotation_monitor_id,
        annotation_transition_id=row.annotation_transition_id,
        fired_at=row.fired_at,
        title=row.title,
        summary=row.summary,
        count=row.count,
        threshold=row.threshold,
        event_ids=tuple(str(item) for item in row.event_ids),
        countries=tuple(str(code) for code in row.countries),
        acknowledged_at=row.acknowledged_at,
        acknowledged_by=row.acknowledged_by,
        report_id=row.report_id,
        created_by=row.created_by,
        team_id=row.team_id,
    )


def _alert_row(alert: Alert) -> AlertRow:
    return AlertRow(
        id=alert.id,
        indicator_id=alert.indicator_id,
        schedule_id=alert.schedule_id,
        annotation_monitor_id=alert.annotation_monitor_id,
        annotation_transition_id=alert.annotation_transition_id,
        fired_at=alert.fired_at,
        title=alert.title,
        summary=alert.summary,
        count=alert.count,
        threshold=alert.threshold,
        event_ids=list(alert.event_ids),
        countries=list(alert.countries),
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        report_id=alert.report_id,
        created_by=alert.created_by,
        team_id=alert.team_id,
    )
