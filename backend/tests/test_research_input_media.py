"""Preview budget and provenance survive media intake without persisting PNG payloads."""

import base64
import hashlib
from dataclasses import asdict, replace

import pytest

from ase.adapters.research_imports import extract_upload
from ase.adapters.research_inputs.importer import DocumentResearchImporter
from ase.adapters.research_inputs.previews import preview_size
from ase.adapters.research_media.models import MediaExtractionResult, MediaFrame
from ase.api.schemas_research_inputs import ResearchInputOut
from ase.application.ports.research_inputs import MAX_PREVIEW_BYTES, InputPreviewFrame
from ase.domain.errors import InvalidRequest, Unauthenticated
from research_input_helpers import NOW, Harness

# A generated fixture PNG envelope; the actual isolated media runner owns image decoding.
PNG_ENVELOPE = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + (1).to_bytes(4, "big") * 2


def frame(seconds: float = 0, size: int = 24) -> MediaFrame:
    data = PNG_ENVELOPE + b"x" * (size - len(PNG_ENVELOPE))
    return MediaFrame(seconds, data, hashlib.sha256(data).hexdigest())


def media(frames: tuple[MediaFrame, ...]) -> MediaExtractionResult:
    return MediaExtractionResult(
        "clip.mp4",
        "video/mp4",
        "a" * 64,
        (),
        ("Extraction does not establish authenticity.",),
        (("duration", "12 seconds, unverified metadata"),),
        frames,
        ("Check the visible details against independent sources.",),
    )


class Runner:
    def __init__(self, result: MediaExtractionResult) -> None:
        self.result = result

    async def run_media(self, data: bytes, filename: str) -> MediaExtractionResult:
        return self.result

    async def run(self, data: bytes, filename: str) -> object:
        return extract_upload(data, filename)


async def test_document_bridge_retains_original_digest_and_no_previews() -> None:
    bridge = DocumentResearchImporter(Runner(media(())))
    result = await bridge.extract(b"Fictional report.", "notes.txt", NOW)
    assert result.sha256 == hashlib.sha256(b"Fictional report.").hexdigest()
    assert result.frames == () and result.events[0].grade == "F6"


async def test_media_preview_filter_keeps_all_frame_evidence_but_bounds_image_bytes() -> None:
    original = media((frame(0, 600_000), frame(6, 600_000), frame(12, 100)))
    bridge = DocumentResearchImporter(Runner(original))
    result = await bridge.extract(b"transient media", "clip.mp4", NOW)
    assert len(result.frames) == 2
    assert sum(len(item.png) for item in result.frames) <= MAX_PREVIEW_BYTES
    assert "omitted" in result.limitations[-1]
    frame_events = [event for event in result.events if event.subtype == "media_frame"]
    assert len(frame_events) == 3
    assert {event.attributes["sample_timestamp_seconds"] for event in frame_events} == {0, 6, 12}
    assert all(event.grade == "F6" and "png" not in event.attributes for event in frame_events)
    harness = Harness()
    pending = harness.store.reserve(harness.actor, "clip.mp4")
    stored = harness.store.put(pending, result)
    assert "frames" not in asdict(stored.receipt)
    response = ResearchInputOut.from_receipt(stored.receipt, stored.frames)
    assert base64.b64decode(response.previews[0].png_base64) == original.frames[0].png
    assert response.previews[0].sha256 == original.frames[0].sha256


@pytest.mark.parametrize("kind", ["count", "size", "signature", "dimension", "hash", "time"])
def test_retained_preview_envelope_limits_and_digest_are_verified(kind: str) -> None:
    original = frame()
    preview = InputPreviewFrame(original.seconds, original.sha256, original.png)
    frames = (preview,)
    if kind == "count":
        frames *= 4
    elif kind == "size":
        frames = (replace(preview, png=b"x" * (MAX_PREVIEW_BYTES + 1)),)
    elif kind == "signature":
        frames = (replace(preview, png=b"not a sanitised PNG"),)
    elif kind == "dimension":
        frames = (replace(preview, png=preview.png[:16] + (513).to_bytes(4, "big") * 2),)
    elif kind == "hash":
        frames = (replace(preview, sha256="0" * 64),)
    else:
        frames = (replace(preview, seconds=float("nan")),)
    with pytest.raises(InvalidRequest):
        preview_size(frames)


async def test_revocation_during_body_upload_is_checked_before_parser_starts() -> None:
    harness = Harness()
    pending = await harness.service.reserve(harness.actor, "notes.txt")
    harness.identity.current = replace(harness.actor, security_version=1)
    with pytest.raises(Unauthenticated):
        await harness.service.execute_reserved(harness.actor, pending, b"private")
    assert harness.extractor.calls == 0 and not harness.store._reservations
