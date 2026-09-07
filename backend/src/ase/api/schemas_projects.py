"""Frozen historical project facts exposed without invented exact dates."""

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    commitment_year: int | None
    implementation_year: int | None
    completion_year: int | None
