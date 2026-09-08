"""Private media evidence references, with no image payloads or authenticity inference."""

from collections.abc import Mapping
from datetime import UTC, datetime

from ase.adapters.research_imports.models import (
    MAX_TEXT_CHARS,
    MAX_UNIT_CHARS,
    MAX_UNITS,
    ImportRejected,
)
from ase.adapters.research_media.models import MediaExtractionResult, MediaFrame
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    JsonScalar,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)

SOURCE_ID = "research_media"
METADATA_GROUP_SIZE = 6


def _common(result: MediaExtractionResult) -> dict[str, JsonScalar]:
    limitations = " ".join(result.limitations)
    attributes: dict[str, JsonScalar] = {
        "filename": result.filename,
        "original_sha256": result.sha256,
        "media_type": result.media_type,
        "timestamp_basis": "upload capture time; original publication and recording times unknown",
        "authenticity": "unknown; extraction is not verification",
        "provenance_status": "unverified upload",
        "extraction_limitations": limitations,
        "limitations_truncated": len(limitations) > 500,
    }
    for index, lead in enumerate(result.verification_leads, 1):
        attributes[f"verification_lead_{index}"] = lead
    return attributes


def _frame_attributes(frame: MediaFrame) -> dict[str, JsonScalar]:
    return {
        "sample_timestamp_seconds": frame.seconds,
        "sample_timestamp_basis": "approximate offset in uploaded media, not a recording date",
        "sample_sha256": frame.sha256,
    }


def events_from_media(result: MediaExtractionResult, captured_at: datetime) -> tuple[Event, ...]:
    """Map a validated worker result to F6 evidence; preview bytes remain upload-response only.

    Metadata is grouped without dropping fields. Its editable date/location claims never set
    event timestamps or geolocation. Verification leads are inert suggestions, never findings.
    """
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ImportRejected("Capture time must include a timezone.")
    if (
        len(result.units) > MAX_UNITS
        or len(result.metadata) > 16
        or len(result.frames) > 3
        or len(result.verification_leads) > 10
        or any(len(unit.text) > MAX_UNIT_CHARS for unit in result.units)
        or sum(len(unit.text) for unit in result.units) > MAX_TEXT_CHARS
    ):
        raise ImportRejected("Media extraction exceeds evidence bounds.")
    captured_at = captured_at.astimezone(UTC)
    common = _common(result)
    events: list[Event] = []

    def add(
        reference: str,
        text: str,
        subtype: str,
        extra: Mapping[str, JsonScalar] | None = None,
    ) -> None:
        if len(events) >= MAX_UNITS or len(text) > MAX_UNIT_CHARS:
            raise ImportRejected("Media extraction exceeds evidence bounds.")
        attributes = {**common, "source_reference": reference, **(extra or {})}
        events.append(
            Event(
                id=event_id(SOURCE_ID, f"{result.sha256}:{subtype}:{len(events)}:{reference}"),
                source_id=SOURCE_ID,
                category=Category.NEWS,
                subtype=subtype,
                title=f"{result.filename}: {reference}"[:300],
                summary=text,
                published_at=None,
                observed_at=captured_at,
                reliability=Reliability.F,
                credibility=Credibility.CANNOT_BE_JUDGED,
                language="und",
                grade_rationale="Uploaded media and OCR: origin and factual accuracy unassessed.",
                tags=frozenset({"private-import", "media-evidence", "unverified"}),
                attributes=freeze_attributes(attributes),
                content_hash=content_hash(text),
            )
        )

    metadata_units = {(f"Media metadata: {key}", value) for key, value in result.metadata}
    frame_references = {
        f"Video sample at approximately {frame.seconds:g} seconds" for frame in result.frames
    }
    for unit in result.units:
        if (unit.reference, unit.text) in metadata_units:
            continue
        if (
            unit.reference in frame_references
            and unit.text == "Sampled frame; visual verification required."
        ):
            continue
        linked_frame = next(
            (
                frame
                for frame in result.frames
                if unit.reference.startswith(
                    f"Video OCR at approximately {frame.seconds:g} seconds"
                )
                or (
                    result.media_type.startswith("image/")
                    and unit.reference.startswith("Image OCR")
                )
            ),
            None,
        )
        add(
            unit.reference,
            unit.text,
            "media_passage",
            _frame_attributes(linked_frame) if linked_frame else None,
        )

    for start in range(0, len(result.metadata), METADATA_GROUP_SIZE):
        group = result.metadata[start : start + METADATA_GROUP_SIZE]
        text = "Unverified media metadata:\n" + "\n".join(f"{key}: {value}" for key, value in group)
        references = {
            f"metadata_reference_{index}": f"Media metadata: {key}"
            for index, (key, _) in enumerate(group, 1)
        }
        add(
            f"Media metadata group {start // METADATA_GROUP_SIZE + 1}",
            text,
            "media_metadata",
            references,
        )

    for frame in result.frames:
        reference = (
            f"Video sample at approximately {frame.seconds:g} seconds"
            if result.media_type.startswith("video/")
            else "Image preview"
        )
        text = (
            f"{reference}. Sanitised derivative SHA-256: {frame.sha256}. "
            "The preview requires visual review and does not establish authenticity."
        )
        add(reference, text, "media_frame", _frame_attributes(frame))
    return tuple(events)
