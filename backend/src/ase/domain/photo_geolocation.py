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


class PhotoObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    photo_id: str = Field(pattern=r"^photo-[1-6]$")
    visual_clues: list[str] = Field(max_length=8)
    limitations: list[str] = Field(min_length=1, max_length=6)


class PhotoShadow(BaseModel):
    """A shadow the model measured by eye: its length as a multiple of the object's height."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    photo_id: str = Field(pattern=r"^photo-[1-6]$")
    shadow_length_to_height: float = Field(ge=0.02, le=50)
    basis: str = Field(min_length=10, max_length=500)


class PhotoAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["candidates", "unknown"]
    summary: str = Field(min_length=1, max_length=1200)
    visual_clues: list[str] = Field(max_length=12)
    candidates: list[PhotoCandidate] = Field(max_length=3)
    verification_steps: list[str] = Field(min_length=1, max_length=10)
    limitations: list[str] = Field(min_length=1, max_length=10)
    photos: list[PhotoObservation] = Field(default_factory=list, max_length=6)
    shadows: list[PhotoShadow] = Field(default_factory=list, max_length=6)
    cross_photo_analysis: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_hypotheses(self) -> "PhotoAssessment":
        if (self.status == "candidates") != bool(self.candidates):
            raise ValueError("Candidates and assessment status disagree.")
        values = self.visual_clues + self.verification_steps + self.limitations
        if len({photo.photo_id for photo in self.photos}) != len(self.photos):
            raise ValueError("Each photograph must appear only once in the assessment.")
        for photo in self.photos:
            values += photo.visual_clues + photo.limitations
        for candidate in self.candidates:
            values += candidate.supporting_clues + candidate.contradictions
            if candidate.coordinates is not None:
                minimum = {"country": 100, "region": 20, "city": 1, "landmark": 0.1}
                if candidate.coordinates.uncertainty_radius_km < minimum[candidate.precision]:
                    raise ValueError("Coordinates claim more precision than the candidate.")
        if any(not value.strip() or len(value) > 500 for value in values):
            raise ValueError("Geolocation clues must be bounded, non-empty text.")
        return self


class SunShadowCheck(BaseModel):
    """Whether a candidate agrees with a reported shadow at the stated capture instant."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    candidate_label: str = Field(min_length=1, max_length=200)
    photo_id: str = Field(pattern=r"^photo-[1-6]$")
    status: Literal["consistent", "inconsistent", "sun_below_horizon", "no_coordinates"]
    captured_at: datetime
    sun_elevation_deg: float | None
    sun_azimuth_deg: float | None
    expected_shadow_ratio: float | None
    observed_shadow_ratio: float
    note: str = Field(min_length=1, max_length=600)


class PhotoImageProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    photo_id: str = Field(pattern=r"^photo-[1-6]$")
    input_id: UUID
    original_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    image_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


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
    photos: list[PhotoImageProvenance] = Field(default_factory=list, max_length=6)
