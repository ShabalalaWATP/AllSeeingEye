"""Compare uncertain project years without converting them to occurrence instants."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from ase.domain.project import ProjectMetadata

MAX_PROJECT_INTERVAL = timedelta(days=30 * 366)


class ProjectYearMatch(StrEnum):
    UNKNOWN = "unknown"
    OUTSIDE = "outside"
    POSSIBLE = "possible"
    WITHIN = "within"


def commitment_bounds(project: ProjectMetadata) -> tuple[datetime, datetime] | None:
    """Uncertainty bounds, not a project's start/end or duration of operation."""
    year = project.commitment_year
    if year is None:
        return None
    return datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC)


def commitment_match(
    project: ProjectMetadata, since: datetime, until: datetime
) -> ProjectYearMatch:
    """Half-open query overlap; a narrow overlap is only a possible temporal match."""
    if (
        any(
            not isinstance(value, datetime) or value.utcoffset() is None for value in (since, until)
        )
        or since >= until
    ):
        raise ValueError("Project queries require an aware positive interval")
    bounds = commitment_bounds(project)
    if bounds is None:
        return ProjectYearMatch.UNKNOWN
    start, end = bounds
    if until <= start or since >= end:
        return ProjectYearMatch.OUTSIDE
    if since <= start and until >= end:
        return ProjectYearMatch.WITHIN
    return ProjectYearMatch.POSSIBLE
