"""Media evidence preserves references and uncertainty without persisting preview bytes."""

import base64
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from ase.adapters.research_imports.models import ExtractedUnit, ImportRejected
from ase.adapters.research_media import MediaTools, extract_media
from ase.adapters.research_media.events import events_from_media
from media_helpers import synthetic_image

NOW = datetime(2026, 9, 6, tzinfo=UTC)


def test_image_metadata_stays_unverified_and_does_not_backdate_or_geolocate() -> None:
    result = extract_media(synthetic_image(metadata=True), "synthetic.png", MediaTools())
    events = events_from_media(result, NOW)
    assert len(events) == 2
    metadata, frame = events
    assert metadata.subtype == "media_metadata" and frame.subtype == "media_frame"
    assert "metadata_datetime: 2026:01:01" in (metadata.summary or "")
    assert all(event.published_at == event.observed_at == NOW for event in events)
    assert all(event.point is None and event.country_iso is None for event in events)
    assert all(
        event.grade == "F6" and event.language == "und" and event.url is None for event in events
    )
    assert frame.attributes["sample_sha256"] == result.frames[0].sha256
    assert frame.attributes["original_sha256"] == result.sha256
    assert frame.attributes["timestamp_basis"].startswith("upload capture time")  # type: ignore[union-attr]
    for event in events:
        assert event.attributes["verification_lead_1"] == result.verification_leads[0]
        with pytest.raises(TypeError):
            event.attributes["authenticity"] = "verified"  # type: ignore[index]


def test_video_ocr_and_samples_preserve_offsets_references_and_hashes_only() -> None:
    image = extract_media(synthetic_image(), "sample.png", MediaTools())
    frame = replace(image.frames[0], seconds=3.5)
    result = replace(
        image,
        filename="sample.mp4",
        media_type="video/mp4",
        frames=(frame,),
        metadata=(),
        units=(
            ExtractedUnit("Video OCR at approximately 3.5 seconds", "Station name observed by OCR"),
            ExtractedUnit(
                "Video sample at approximately 3.5 seconds",
                "Sampled frame; visual verification required.",
            ),
        ),
    )
    events = events_from_media(result, NOW)
    assert [event.subtype for event in events] == ["media_passage", "media_frame"]
    assert events[0].attributes["source_reference"] == result.units[0].reference
    assert all(event.attributes["sample_timestamp_seconds"] == 3.5 for event in events)
    assert all(event.attributes["sample_sha256"] == frame.sha256 for event in events)
    rendered = repr(events)
    assert base64.b64encode(frame.png).decode() not in rendered
    assert repr(frame.png) not in rendered and "data:image" not in rendered
    assert all(
        not isinstance(value, bytes) for event in events for value in event.attributes.values()
    )


def test_grouped_metadata_preserves_all_fields_without_duplicate_passages() -> None:
    base = extract_media(synthetic_image(), "test.png", MediaTools())
    metadata = tuple((f"field_{index}", f"value_{index}") for index in range(16))
    result = replace(
        base,
        metadata=metadata,
        frames=(),
        units=tuple(ExtractedUnit(f"Media metadata: {key}", value) for key, value in metadata),
    )
    events = events_from_media(result, NOW)
    assert len(events) == 3
    text = "\n".join(event.summary or "" for event in events)
    for key, value in metadata:
        assert f"{key}: {value}" in text
        assert any(f"Media metadata: {key}" in event.attributes.values() for event in events)
    assert all(event.subtype == "media_metadata" for event in events)


def test_media_unavailable_does_not_invent_evidence_and_naive_capture_is_rejected() -> None:
    result = extract_media(b"unprocessed", "test.mp4", MediaTools())
    assert events_from_media(result, NOW) == ()
    with pytest.raises(ImportRejected, match="timezone"):
        events_from_media(result, NOW.replace(tzinfo=None))


def test_event_ids_are_stable_and_duplicate_references_do_not_collide() -> None:
    base = extract_media(synthetic_image(), "test.png", MediaTools())
    result = replace(
        base,
        metadata=(),
        frames=(),
        units=(ExtractedUnit("same", "one"), ExtractedUnit("same", "two")),
    )
    first = events_from_media(result, NOW)
    second = events_from_media(result, NOW.astimezone(timezone(timedelta(hours=2))))
    assert first == second and len({event.id for event in first}) == 2


@pytest.mark.parametrize("kind", ["units", "metadata", "frames", "leads", "text", "combined"])
def test_evidence_count_and_text_limits_are_explicit(kind: str) -> None:
    base = extract_media(synthetic_image(), "test.png", MediaTools())
    changes: dict[str, object] = {
        "units": (ExtractedUnit("ref", "text"),) * 201,
        "metadata": (("key", "value"),) * 17,
        "frames": (base.frames[0],) * 4,
        "leads": ("lead",) * 11,
        "text": (ExtractedUnit("ref", "x" * 1801),),
        "combined": (ExtractedUnit("ref", "text"),) * 200,
    }
    field = {"leads": "verification_leads", "text": "units", "combined": "units"}.get(kind, kind)
    result = replace(base, **{field: changes[kind]})  # type: ignore[arg-type]
    with pytest.raises(ImportRejected, match="bounds"):
        events_from_media(result, NOW)
