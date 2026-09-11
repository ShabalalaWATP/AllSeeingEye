"""Validated visual hypotheses, never a verified position or model confidence score."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.llm import LlmProvider


class PhotoCoordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    uncertainty_radius_km: float = Field(ge=0.1, le=20_000)
    basis: str = Field(min_length=10, max_length=500)


class PhotoCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    label: str = Field(min_length=1, max_length=200)
    country_iso: str | None = Field(pattern=r"^[A-Z]{2}$")
    precision: Literal["country", "region", "city", "landmark"]
    supporting_clues: list[str] = Field(min_length=1, max_length=8)
    contradictions: list[str] = Field(max_length=8)
    coordinates: PhotoCoordinates | None


class PhotoAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["candidates", "unknown"]
    summary: str = Field(min_length=1, max_length=1200)
    visual_clues: list[str] = Field(max_length=12)
    candidates: list[PhotoCandidate] = Field(max_length=3)
    verification_steps: list[str] = Field(min_length=1, max_length=10)
    limitations: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_hypotheses(self) -> "PhotoAssessment":
        if (self.status == "candidates") != bool(self.candidates):
            raise ValueError("Candidates and assessment status disagree.")
        values = self.visual_clues + self.verification_steps + self.limitations
        for candidate in self.candidates:
            values += candidate.supporting_clues + candidate.contradictions
            if candidate.coordinates is not None:
                minimum = {"country": 100, "region": 20, "city": 1, "landmark": 0.1}
                if candidate.coordinates.uncertainty_radius_km < minimum[candidate.precision]:
                    raise ValueError("Coordinates claim more precision than the candidate.")
        if any(not value.strip() or len(value) > 500 for value in values):
            raise ValueError("Geolocation clues must be bounded, non-empty text.")
        return self


class PhotoProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    profile_id: UUID
    profile_revision: int
    provider: LlmProvider
    configured_model: str
    returned_model: str
    analysed_at: datetime
    original_sha256: str
    image_sha256: str
