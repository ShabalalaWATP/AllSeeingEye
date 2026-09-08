"""Explicit frozen evidence contract, including provenance absent from legacy records."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr

from ase.api.schemas_observations import EvidenceGeometryOut, ObservationOut
from ase.api.schemas_projects import ProjectOut
from ase.api.schemas_source_ratings import SourceRatingOut
from ase.domain.source_dates import SourceDate
from ase.domain.text_transformations import TextTransformation


class EvidenceAttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: StrictStr | StrictInt | StrictFloat | StrictBool | None


class ReportEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    event_id: str
    source_id: str
    source_name: str
    independence_key: str
    category: str
    title: str
    summary: str | None
    url: str | None
    published_at: datetime | None
    captured_at: datetime
    grade: str
    reliability: str
    credibility: int
    grade_rationale: str
    lon: float | None
    lat: float | None
    country_iso: str | None
    content_hash: str
    instrument: bool
    flags: list[str]
    archive_url: str | None
    title_en: str | None = None
    language: str | None = None
    geo_confidence: str | None = None
    observed_at: datetime | None = None
    story_id: str | None = None
    source_rating: SourceRatingOut | None = None
    attributes: list[EvidenceAttributeOut] = Field(default_factory=list)
    geometry: EvidenceGeometryOut | None = None
    observation: ObservationOut | None = None
    project: ProjectOut | None = None
    transformations: list[TextTransformation] = Field(default_factory=list)
    source_dates: list[SourceDate] = Field(default_factory=list)
