"""Frozen research coverage response contract."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_research_plan import ResearchPlanOut
from ase.domain.research import CollectionStatus


class CollectionAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_name: str
    status: CollectionStatus
    result_count: int
    explanation: str
    language: str | None


class CollectionPassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    terms: list[str]
    attempts: list[CollectionAttemptOut]
    plan: ResearchPlanOut | None = None


class ResearchReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question: str
    mode: str
    focus: str
    languages: list[str]
    terms: list[str]
    since: datetime
    until: datetime
    attempts: list[CollectionAttemptOut]
    collected_items: int
    policy_version: str
    time_basis: Literal["publication", "acquisition_or_publication"] = "publication"
    plan: ResearchPlanOut | None = None

    passes: list[CollectionPassOut] = Field(default_factory=list, max_length=2)
