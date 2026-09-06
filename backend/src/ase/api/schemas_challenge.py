"""Frozen all-judgement challenge response, separate from legacy single advocacy."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.api.schemas_research import CollectionAttemptOut
from ase.domain.doctrine import Confidence


class ChallengeAdvocacyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    target: str
    argument: str
    evidence: list[str]
    lower_confidence: bool
    rationale: str
    confidence_before: Confidence | None
    confidence_after: Confidence | None


class ChallengeSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    judgement_id: str
    statement: str
    terms: list[str]
    status: Literal["attempted", "unavailable", "plan_missing", "budget_exhausted"]
    attempts: list[CollectionAttemptOut]
    collected_items: int
    selected_event_ids: list[str]
    explanation: str


class ChallengeReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    judgement_id: str
    statement: str
    status: Literal["completed", "unavailable", "invalid"]
    advocacy: ChallengeAdvocacyOut | None
    explanation: str


class ReportChallengeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    searches: list[ChallengeSearchOut]
    reviews: list[ChallengeReviewOut]
    redrafted: bool
    method_version: str
    request_limit: int
    seconds_limit: int
    limitations: list[str]
