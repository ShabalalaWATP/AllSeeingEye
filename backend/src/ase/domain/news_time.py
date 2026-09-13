"""GDELT indexing time is usable for map recency, never publication-window evidence."""

import re
from datetime import UTC, datetime

from ase.domain.events import Category, Event
from ase.domain.source_dates import SourceDate


def news_index_date(raw: str) -> SourceDate:
    try:
        if not re.fullmatch(r"[0-9]{14}", raw):
            raise ValueError("Expected a complete GDELT indexing timestamp")
        value = datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        value = None
    return SourceDate(
        field="DATEADDED",
        raw_text=raw[:300] or "(missing)",
        role="unspecified",
        calendar="gregorian",
        basis="source_spec",
        precision="instant" if value else "unknown",
        status="resolved" if value else "invalid",
        method="gdelt-dateadded-utc-v1",
        value=value,
        limitations=("GDELT indexing time, not publisher publication or event occurrence time.",),
    )


def news_indexing_time(event: Event) -> datetime | None:
    if event.source_id != "gdelt_news" or event.category is not Category.NEWS:
        return None
    for date in event.source_dates:
        if date.field == "DATEADDED" and date == news_index_date(date.raw_text):
            return date.value
    return None
