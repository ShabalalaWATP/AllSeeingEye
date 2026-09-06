"""Exact saved-map provenance for a derived area research report."""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from ase.domain.research_area import ResearchArea, area_from_dict, area_to_dict


@dataclass(frozen=True, slots=True)
class MapResearchOrigin:
    view_id: UUID
    revision_id: UUID
    report_id: UUID
    report_version_id: UUID
    report_version_number: int
    content_sha256: str
    evidence_sha256: str
    area: ResearchArea

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.view_id, self.revision_id, self.report_id, self.report_version_id)
        ):
            raise ValueError("Invalid map origin identity")
        if type(self.report_version_number) is not int or self.report_version_number < 1:
            raise ValueError("Invalid map origin report version")
        if any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (self.content_sha256, self.evidence_sha256)
        ):
            raise ValueError("Invalid map origin integrity hash")
        if not isinstance(self.area, ResearchArea):
            raise ValueError("Map origin needs a canonical research area")


def origin_to_dict(origin: MapResearchOrigin | None) -> dict[str, Any] | None:
    if origin is None:
        return None
    return {
        "view_id": str(origin.view_id),
        "revision_id": str(origin.revision_id),
        "report_id": str(origin.report_id),
        "report_version_id": str(origin.report_version_id),
        "report_version_number": origin.report_version_number,
        "content_sha256": origin.content_sha256,
        "evidence_sha256": origin.evidence_sha256,
        "area": area_to_dict(origin.area),
    }


def origin_from_dict(value: Any) -> MapResearchOrigin | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {
        "view_id",
        "revision_id",
        "report_id",
        "report_version_id",
        "report_version_number",
        "content_sha256",
        "evidence_sha256",
        "area",
    }:
        raise ValueError("Invalid saved map origin")
    area = area_from_dict(value["area"])
    if area is None:
        raise ValueError("Saved map origin has no area")
    return MapResearchOrigin(
        UUID(value["view_id"]),
        UUID(value["revision_id"]),
        UUID(value["report_id"]),
        UUID(value["report_version_id"]),
        value["report_version_number"],
        value["content_sha256"],
        value["evidence_sha256"],
        area,
    )
