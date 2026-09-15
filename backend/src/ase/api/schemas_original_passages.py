"""Authorised, expiry-bound exact source passage response."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OriginalPassageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ref: UUID
    evidence_label: str
    source_id: str
    issuer: str
    document_version_id: str
    original_sha256: str
    passage_id: str
    passage_sha256: str
    source_reference: str
    page: int | None
    text: str
    published_at: datetime | None
    retrieved_at: datetime
    expires_at: datetime
    original_language: str
    permitted_use: str
