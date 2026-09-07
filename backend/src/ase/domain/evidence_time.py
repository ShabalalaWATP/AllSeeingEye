"""Explicit retrieval time bases, never a substitute for evidence timestamps."""

from datetime import datetime
from enum import StrEnum

from ase.domain.events import Event


class EvidenceTimeBasis(StrEnum):
    PUBLICATION = "publication"
    # Mixed area evidence: observations use acquisition, reporting uses publication.
    RESEARCH = "acquisition_or_publication"


def evidence_time(
    event: Event, basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION
) -> datetime | None:
    if not isinstance(basis, EvidenceTimeBasis):
        raise ValueError("Unknown evidence time basis")
    value = (
        event.observation.acquired_at
        if basis is EvidenceTimeBasis.RESEARCH and event.observation is not None
        else event.published_at
    )
    # An unknown/naive date cannot acquire recency from the retrieval timestamp.
    return value if value is not None and value.utcoffset() is not None else None
