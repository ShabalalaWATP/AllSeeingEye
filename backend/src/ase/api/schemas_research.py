"""Frozen research coverage response contract."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_research_plan import QueryVariantIn, ResearchPlanOut
from ase.api.schemas_web_research import WebResearchOut
from ase.domain.registry_identifiers import RegistryLookup
from ase.domain.research import CollectionStatus


class CollectionAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_name: str
    status: CollectionStatus
    result_count: int
    explanation: str
    language: str | None
    task_id: str | None = None
    purpose: Literal["baseline", "challenge", "disambiguation"] = "baseline"
    candidate_id: str | None = None
    registry_lookup: RegistryLookup | None = None
    query_variant: QueryVariantIn | None = None


class CollectionPassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    terms: list[str]
    attempts: list[CollectionAttemptOut]
    plan: ResearchPlanOut | None = None


class OriginalFollowupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_label: str
    event_id: str
    source_id: str
    status: Literal["acquired", "headline_only", "unavailable"]
    reason: str
    candidate_id: str | None = None
    passage_ref: UUID | None = None
    passage_id: str | None = None
    document_version_id: str | None = None
    transport_requests: int | None = 0
    transport_requests_reserved: int = 0


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
    time_basis: Literal["publication", "acquisition_or_publication", "recorded_time"] = (
        "publication"
    )
    plan: ResearchPlanOut | None = None

    passes: list[CollectionPassOut] = Field(default_factory=list, max_length=2)
    web_research: WebResearchOut | None = None
    original_followup: list[OriginalFollowupOut] = Field(default_factory=list, max_length=10)
