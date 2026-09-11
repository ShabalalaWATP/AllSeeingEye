"""Explicit image disclosure and bounded, unverified visual research results."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_research_inputs import ResearchInputOut
from ase.domain.photo_geolocation import PhotoAssessment, PhotoProvenance


class PhotoGeolocationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(default="Where might this photograph have been taken?", max_length=2000)
    hints: str = Field(default="", max_length=1000)
    team_id: UUID | None = None
    consent_to_send_image: Literal[True]


class PhotoGeolocationOut(PhotoAssessment):
    input: ResearchInputOut
    provenance: PhotoProvenance
    candidate_status: Literal["unverified"] = "unverified"
