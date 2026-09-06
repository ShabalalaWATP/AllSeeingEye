"""Exact authorised map provenance accompanying a research preview."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_research_area import ResearchAreaOut


class MapResearchOriginOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    view_id: UUID
    revision_id: UUID
    report_id: UUID
    report_version_id: UUID
    report_version_number: int = Field(gt=0)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    area: ResearchAreaOut
