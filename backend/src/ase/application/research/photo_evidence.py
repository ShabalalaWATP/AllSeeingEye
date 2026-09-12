"""Keep scene hypotheses with model provenance, outside the map's verified location fields."""

from ase.domain.events import (
    Category,
    Credibility,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.photo_geolocation import PhotoAssessment, PhotoProvenance

LIMITATIONS = (
    "AI visual hypotheses are unverified, not identification or proof of a location.",
    "Only a sanitised preview up to 512 pixels was analysed; fine details may be unreadable.",
    "No reverse-image search, source authentication or independent site verification was done.",
)


def photo_events(assessment: PhotoAssessment, provenance: PhotoProvenance) -> tuple[Event, ...]:
    sections = [
        ("Assessment", assessment.summary),
        ("Visible clues", "\n".join(assessment.visual_clues)),
        ("Verification steps", "\n".join(assessment.verification_steps)),
        ("Limitations", "\n".join((*LIMITATIONS, *assessment.limitations))),
        (
            "Analysis provenance",
            provenance.model_dump_json(exclude={"photos": {"__all__": {"input_id"}}}),
        ),
    ]
    for photo in assessment.photos:
        sections.append((f"Observations: {photo.photo_id}", photo.model_dump_json()))
    if assessment.cross_photo_analysis:
        sections.append(("Cross-photo analysis", assessment.cross_photo_analysis))
    for candidate in assessment.candidates:
        sections.append(("Unverified candidate: " + candidate.label, candidate.model_dump_json()))
    events: list[Event] = []
    # Split long sections at a fixed bound without dropping model output.
    for heading, text in sections:
        for offset in range(0, len(text), 1400):
            summary = "UNVERIFIED AI VISUAL HYPOTHESIS. " + text[offset : offset + 1400]
            reference = (
                f"{provenance.image_sha256}:{provenance.analysed_at.isoformat()}:{len(events)}"
            )
            events.append(
                Event(
                    id=event_id("research_media", reference),
                    source_id="research_media",
                    category=Category.NEWS,
                    subtype="photo_geolocation_hypothesis",
                    title=heading[:300],
                    summary=summary,
                    published_at=None,
                    observed_at=provenance.analysed_at,
                    language="en",
                    reliability=Reliability.F,
                    credibility=Credibility.CANNOT_BE_JUDGED,
                    grade_rationale="Generated scene hypothesis, not independent factual evidence.",
                    tags=frozenset(
                        {"private-import", "media-evidence", "unverified", "ai-generated"}
                    ),
                    attributes=freeze_attributes(
                        {
                            "provenance_status": "unverified AI visual hypothesis",
                            "original_sha256": provenance.original_sha256,
                            "sample_sha256": provenance.image_sha256,
                            "model_profile_id": str(provenance.profile_id),
                            "model_profile_revision": provenance.profile_revision,
                            "model_provider": provenance.provider.value,
                            "configured_model": provenance.configured_model,
                            "returned_model": provenance.returned_model,
                            "analysis_time": provenance.analysed_at.isoformat(),
                            "timestamp_basis": "analysis time; image capture/publication unknown",
                            "source_reference": heading,
                        }
                    ),
                    content_hash=content_hash(summary),
                )
            )
    return tuple(events)
