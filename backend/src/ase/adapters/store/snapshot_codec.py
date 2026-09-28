"""Strict JSON records for retained public events in the live-store snapshot (ADR 0022).

Only the fields of the public `Event` are encoded. A record with an unknown field,
a missing required field or a value the domain rejects raises `ValueError`.
"""

import math
from dataclasses import MISSING, fields
from datetime import datetime
from types import MappingProxyType
from typing import Any

from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    JsonScalar,
    Point,
    Reliability,
)
from ase.domain.evidence_geometry import geometry_from_dict, geometry_to_dict
from ase.domain.observation import observation_from_dict, observation_to_dict
from ase.domain.project import project_from_dict, project_to_dict
from ase.domain.source_provenance_records import (
    dates_from_list,
    provenance_to_dict,
    transformations_from_list,
)

EVENT_FIELDS = frozenset(field.name for field in fields(Event))
# Fields without a default must be present; defaulted fields may be absent in older files.
REQUIRED_FIELDS = frozenset(
    field.name
    for field in fields(Event)
    if field.default is MISSING and field.default_factory is MISSING
)
MAX_TEXT = 20_000
MAX_KEY = 200
MAX_TAGS = 200
MAX_ATTRIBUTE_KEYS = 100


def event_to_record(event: Event) -> dict[str, Any]:
    point = event.point
    return {
        "id": event.id,
        "source_id": event.source_id,
        "category": event.category.value,
        "subtype": event.subtype,
        "title": event.title,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "observed_at": event.observed_at.isoformat(),
        "reliability": event.reliability.value,
        "summary": event.summary,
        "url": event.url,
        "language": event.language,
        "title_en": event.title_en,
        "point": [point.lon, point.lat] if point is not None else None,
        "geo_confidence": event.geo_confidence.value,
        "country_iso": event.country_iso,
        "tags": sorted(event.tags),
        "severity": event.severity,
        "credibility": int(event.credibility),
        "grade_rationale": event.grade_rationale,
        "story_id": event.story_id,
        "attributes": dict(event.attributes),
        "content_hash": event.content_hash,
        "geometry": geometry_to_dict(event.geometry) if event.geometry else None,
        "observation": observation_to_dict(event.observation) if event.observation else None,
        "project": project_to_dict(event.project) if event.project else None,
        "transformations": [provenance_to_dict(row) for row in event.transformations],
        "source_dates": [provenance_to_dict(row) for row in event.source_dates],
    }


def event_from_record(record: object) -> Event:
    if not isinstance(record, dict) or not REQUIRED_FIELDS <= set(record) <= EVENT_FIELDS:
        raise ValueError("Snapshot event has unknown or missing fields")
    try:
        return _decode(record)
    except (TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid snapshot event") from exc


def _decode(record: dict[str, Any]) -> Event:
    get = record.get
    return Event(
        id=_text(record["id"], MAX_KEY, required=True),
        source_id=_text(record["source_id"], MAX_KEY, required=True),
        category=Category(_text(record["category"], MAX_KEY)),
        subtype=_text(record["subtype"], MAX_KEY),
        title=_text(record["title"]),
        published_at=_optional_time(record["published_at"]),
        observed_at=_time(record["observed_at"]),
        reliability=Reliability(_text(record["reliability"], MAX_KEY)),
        summary=_optional_text(get("summary")),
        url=_optional_text(get("url")),
        language=_text(get("language", "en"), MAX_KEY),
        title_en=_optional_text(get("title_en")),
        point=_point(get("point")),
        geo_confidence=GeoConfidence(_text(get("geo_confidence", "none"), MAX_KEY)),
        country_iso=_optional_text(get("country_iso"), MAX_KEY),
        tags=_tags(get("tags", [])),
        severity=_number(get("severity")),
        credibility=Credibility(_integer(get("credibility", 6))),
        grade_rationale=_text(get("grade_rationale", "")),
        story_id=_optional_text(get("story_id"), MAX_KEY),
        attributes=_attributes(get("attributes", {})),
        content_hash=_text(get("content_hash", ""), MAX_KEY),
        geometry=geometry_from_dict(get("geometry")),
        observation=observation_from_dict(get("observation")),
        project=project_from_dict(get("project")),
        transformations=transformations_from_list(get("transformations", [])),
        source_dates=dates_from_list(get("source_dates", [])),
    )


def _text(value: object, limit: int = MAX_TEXT, *, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value):
        raise ValueError("Invalid snapshot text")
    return value


def _optional_text(value: object, limit: int = MAX_TEXT) -> str | None:
    return None if value is None else _text(value, limit)


def _time(value: object) -> datetime:
    parsed = datetime.fromisoformat(_text(value, 64))
    if parsed.utcoffset() is None:
        raise ValueError("Snapshot times require a timezone")
    return parsed


def _optional_time(value: object) -> datetime | None:
    return None if value is None else _time(value)


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("Expected an integer")
    return value


def _number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError("Expected a finite number")
    # Keep the JSON number type so restored values serialise exactly as before.
    return value


def _point(value: object) -> Point | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("Invalid snapshot point")
    lon, lat = (_number(item) for item in value)
    if lon is None or lat is None:
        raise ValueError("Invalid snapshot point")
    return Point(lon=lon, lat=lat)


def _tags(value: object) -> frozenset[str]:
    if not isinstance(value, list) or len(value) > MAX_TAGS:
        raise ValueError("Invalid snapshot tags")
    return frozenset(_text(tag, MAX_KEY) for tag in value)


def _attributes(value: object) -> MappingProxyType[str, JsonScalar]:
    if not isinstance(value, dict) or len(value) > MAX_ATTRIBUTE_KEYS:
        raise ValueError("Invalid snapshot attributes")
    for key, item in value.items():
        _text(key, MAX_KEY)
        if isinstance(item, str):
            _text(item)
        elif type(item) is float and not math.isfinite(item):
            raise ValueError("Snapshot attributes must be finite")
        elif item is not None and type(item) not in (bool, int, float):
            raise ValueError("Snapshot attributes must be JSON scalars")
    return MappingProxyType(dict(value))
