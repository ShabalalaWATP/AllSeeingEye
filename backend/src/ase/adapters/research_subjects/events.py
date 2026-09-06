"""New subject providers never inherit a platform or official-host reliability grade."""

from collections.abc import Mapping
from datetime import datetime

from ase.adapters.research_records.records import record_event
from ase.domain.events import Category, Event, JsonScalar, Reliability


def subject_event(
    source_id: str,
    key: str,
    title: str,
    summary: str,
    url: str,
    observed: datetime,
    *,
    category: Category,
    attributes: Mapping[str, JsonScalar],
    published: datetime | None = None,
) -> Event:
    return record_event(
        source_id,
        key,
        title,
        summary,
        url,
        observed,
        category=category,
        attributes=attributes,
        published=published,
    ).with_changes(
        reliability=Reliability.F,
        grade_rationale="Unassessed source reliability and item credibility. "
        "A registry, scholarly index or official host does not verify the underlying claim.",
    )
