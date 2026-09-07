"""Explicit retrieval time bases, never a substitute for evidence timestamps."""

from datetime import UTC, datetime
from enum import StrEnum

from ase.domain.events import Event
from ase.domain.project_time import commitment_bounds


class EvidenceTimeBasis(StrEnum):
    PUBLICATION = "publication"
    # Mixed area evidence: observations use acquisition, reporting uses publication.
    RESEARCH = "acquisition_or_publication"
    RECORDED = "recorded_time"


def evidence_time(
    event: Event, basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION
) -> datetime | None:
    if not isinstance(basis, EvidenceTimeBasis):
        raise ValueError("Unknown evidence time basis")
    if basis is EvidenceTimeBasis.RECORDED and event.project is not None:
        return None  # A commitment year has no exact occurrence timestamp.
    value = (
        event.observation.acquired_at
        if basis in (EvidenceTimeBasis.RESEARCH, EvidenceTimeBasis.RECORDED)
        and event.observation is not None
        else event.published_at
    )
    # An unknown/naive date cannot acquire recency from the retrieval timestamp.
    return value if value is not None and value.utcoffset() is not None else None


def publication_order(event: Event) -> datetime:
    """Comparison-only sentinel, never stored or displayed as a publication date."""
    return evidence_time(event) or datetime.min.replace(tzinfo=UTC)


def evidence_matches_time(
    event: Event,
    basis: EvidenceTimeBasis,
    since: datetime | None,
    until: datetime | None,
    *,
    include_unknown: bool = False,
) -> bool:
    """Match instants or project-year uncertainty extents against half-open bounds."""
    timestamp = evidence_time(event, basis)
    if basis is EvidenceTimeBasis.RECORDED and event.project is not None:
        bounds = commitment_bounds(event.project)
        if bounds is None:
            return include_unknown or (since is None and until is None)
        start, end = bounds
        return (since is None or end > since) and (until is None or start < until)
    if timestamp is None:
        return include_unknown or (since is None and until is None)
    return (since is None or timestamp >= since) and (until is None or timestamp < until)


def evidence_order(event: Event, basis: EvidenceTimeBasis) -> datetime:
    """Comparison key only; year bounds are never returned as occurrence timestamps."""
    if basis is EvidenceTimeBasis.RECORDED and event.project is not None:
        bounds = commitment_bounds(event.project)
        return bounds[0] if bounds else datetime.min.replace(tzinfo=UTC)
    return evidence_time(event, basis) or datetime.min.replace(tzinfo=UTC)
