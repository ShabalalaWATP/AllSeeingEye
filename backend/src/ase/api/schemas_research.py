"""Frozen research coverage response contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ase.domain.research import CollectionStatus


class CollectionAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_name: str
    status: CollectionStatus
    result_count: int
    explanation: str
    language: str | None


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
