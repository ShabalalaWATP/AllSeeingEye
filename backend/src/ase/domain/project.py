"""Historical project facts with year precision, never fabricated event timestamps."""

import re
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    dataset_id: str
    release_id: str
    project_id: str
    source_sha256: str
    recipient_iso3: str
    reported_status: str
    precision: str
    attribution: str
    data_licence: str
    geometry_licence: str
    limitations: str
    commitment_year: int | None = None
    implementation_year: int | None = None
    completion_year: int | None = None

    def __post_init__(self) -> None:
        for value, limit in (
            (self.dataset_id, 120),
            (self.release_id, 120),
            (self.project_id, 120),
            (self.reported_status, 300),
            (self.precision, 100),
            (self.attribution, 1000),
            (self.data_licence, 300),
            (self.geometry_licence, 300),
            (self.limitations, 2000),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > limit
                or any(ord(char) < 32 for char in value)
            ):
                raise ValueError("Project metadata is missing, invalid or oversized")
            value.encode("utf-8")
        if not isinstance(self.source_sha256, str) or not re.fullmatch(
            r"[a-f0-9]{64}", self.source_sha256
        ):
            raise ValueError("Project provenance requires a SHA-256 digest")
        if not isinstance(self.recipient_iso3, str) or not re.fullmatch(
            r"[A-Z]{3}", self.recipient_iso3
        ):
            raise ValueError("Project recipient requires an ISO alpha-3 code")
        for year in (self.commitment_year, self.implementation_year, self.completion_year):
            # The next year must remain representable for half-open comparison bounds.
            if year is not None and (type(year) is not int or not 1 <= year <= 9998):
                raise ValueError("Project year must be an integer from 1 to 9998 or unknown")


def project_to_dict(value: ProjectMetadata) -> dict[str, Any]:
    return asdict(value)


def project_from_dict(value: Any) -> ProjectMetadata | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {
        field.name for field in fields(ProjectMetadata)
    }:
        raise ValueError("Invalid frozen project metadata")
    try:
        return ProjectMetadata(**value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid frozen project metadata") from exc
