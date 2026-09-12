"""Bounded comparison against a subscription's authorised previous successful report.

Retrieval novelty is not evidential quality or proof of a changed situation. Unchanged
items remain available for context and independent corroboration.
"""

import hashlib
import json
from collections.abc import Sequence

from ase.domain.events import Event
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import freeze_evidence_attributes
from ase.domain.report_records import ReportVersion

CAPTURE_ATTRIBUTES = frozenset({"retrieved_at", "captured_at", "fetched_at", "last_fetched_at"})


def content_signature(item: Event | EvidenceItem) -> str:
    """Ignore labels, URLs, capture times and IDs which can change on each collection."""
    attributes = (
        freeze_evidence_attributes(item.attributes) if isinstance(item, Event) else item.attributes
    )
    if isinstance(item, Event):
        lon, lat = (item.point.lon, item.point.lat) if item.point else (None, None)
    else:
        lon, lat = item.lon, item.lat
    payload = (
        " ".join(item.title.casefold().split()),
        " ".join((item.summary or "").casefold().split()),
        lon,
        lat,
        tuple(
            sorted(
                (attribute.key, attribute.value)
                for attribute in attributes
                if attribute.key.casefold() not in CAPTURE_ATTRIBUTES
            )
        ),
    )
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def previous_signatures(previous: ReportVersion | None) -> frozenset[str]:
    return (
        frozenset(content_signature(item) for item in previous.evidence)
        if previous
        else frozenset()
    )


def update_guidance(
    previous: ReportVersion | None,
    items: Sequence[EvidenceItem],
    seen: frozenset[str] = frozenset(),
    *,
    previous_missing: bool = False,
) -> str | None:
    if previous is None and not seen and not previous_missing:
        return None
    signatures = previous_signatures(previous) | seen
    unchanged = [item.label for item in items if content_signature(item) in signatures]
    fresh = [item.label for item in items if content_signature(item) not in signatures]
    return (
        "Subscription update compared with retained coverage fingerprints. "
        + (
            f"Previous successful edition: {previous.created_at.isoformat()}. "
            if previous
            else "The previous report is unavailable; state this comparison limitation. "
        )
        + "This comparison is of captured content, not proof "
        "of a new event or independently verified change. Prior coverage is context only. "
        "Lead with supported new developments and materially changed facts. Avoid retelling "
        "unchanged stories, retaining only context needed to understand the current situation. "
        "New or changed captured items: " + (", ".join(fresh) or "none") + ". "
        "Unchanged captured items: " + (", ".join(unchanged) or "none") + ". "
        "Compare publication and observation dates, duplication and syndicated reporting before "
        "describing anything as new. If no meaningful update is supported, say 'No material "
        "update was identified in the sources checked', include the relevant limitations, and "
        "give only a brief situation summary. Never claim nothing happened or fill the report "
        "with invented developments. Cite only the current supplied evidence labels."
    )
