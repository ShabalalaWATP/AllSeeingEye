"""Conservative retained-event memory accounting."""

import json

from ase.domain.events import Event
from ase.domain.project import project_to_dict
from ase.domain.source_provenance_records import provenance_size

EVENT_OVERHEAD_BYTES = 1_024


def estimate_bytes(event: Event) -> int:
    text = (
        event.id,
        event.source_id,
        event.subtype,
        event.title,
        event.summary,
        event.url,
        event.language,
        event.title_en,
        event.country_iso,
        event.grade_rationale,
        event.story_id,
        event.content_hash,
    )
    size = EVENT_OVERHEAD_BYTES + 4 * sum(len(value or "") for value in text)
    size += sum(96 + 4 * (len(key) + len(str(value))) for key, value in event.attributes.items())
    size += sum(64 + 4 * len(tag) for tag in event.tags)
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
