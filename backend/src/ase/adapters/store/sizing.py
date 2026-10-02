"""Conservative retained-event memory accounting."""

import json
from collections.abc import Iterator, Mapping
from datetime import datetime
from itertools import groupby

from ase.application.ports.feeds import CategoryStats, StoreStats
from ase.domain.events import Category, Event
from ase.domain.project import project_to_dict
from ase.domain.source_provenance_records import provenance_size

EVENT_OVERHEAD_BYTES = 1_024


def oldest_first(events: Mapping[str, Event]) -> Iterator[str]:
    """Sort observations once, then order only equal-time groups needed for eviction."""

    def observed(identifier: str) -> datetime:
        return events[identifier].observed_at

    for _, identifiers in groupby(sorted(events, key=observed), key=observed):
        yield from sorted(identifiers)


def estimate_bytes(event: Event) -> int:
    size = EVENT_OVERHEAD_BYTES + 4 * (
        len(event.id or "")
        + len(event.source_id or "")
        + len(event.subtype or "")
        + len(event.title or "")
        + len(event.summary or "")
        + len(event.url or "")
        + len(event.language or "")
        + len(event.title_en or "")
        + len(event.country_iso or "")
        + len(event.grade_rationale or "")
        + len(event.story_id or "")
        + len(event.content_hash or "")
    )
    for key, value in event.attributes.items():
        size += 96 + 4 * (len(key) + len(str(value)))
    for tag in event.tags:
        size += 64 + 4 * len(tag)
    if event.geometry is not None:
        geometry = event.geometry
        size += len(geometry.source_geometry.encode("utf-8"))
        size += (
            sum(
                len(value.encode("utf-8"))
                for value in (
                    geometry.precision,
                    geometry.method,
                    geometry.source_id,
                    geometry.attribution,
                )
            )
            + 256
        )
    if event.observation is not None:
        observation = event.observation
        size += (
            sum(
                len(value.encode("utf-8"))
                for value in (
                    observation.collection_id,
                    observation.item_id,
                    observation.limitations,
                )
            )
            + 256
        )
    if event.project is not None:
        size += (
            len(json.dumps(project_to_dict(event.project), ensure_ascii=False).encode("utf-8"))
            + 256
        )
    size += provenance_size(event.transformations, event.source_dates)
    return size


def store_stats(
    events: Mapping[str, Event],
    categories: Mapping[Category, set[str]],
    estimated: int,
    budget: int,
) -> StoreStats:
    per_category = []
    for category, ids in sorted(categories.items(), key=lambda item: item[0].value):
        if ids:
            times = [events[identifier].observed_at for identifier in ids]
            per_category.append(CategoryStats(category, len(ids), min(times), max(times)))
    return StoreStats(len(events), estimated, budget, tuple(per_category))
