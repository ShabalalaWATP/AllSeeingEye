"""Typed frozen context disclosures; all declared names and URLs remain untrusted data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.api.schemas_report_evidence import EvidenceAttributeOut


class ResearchTimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_label: str
    title: str
    published_at: datetime
    captured_at: datetime
    observed_at: datetime | None
    timestamp_basis: str | None
    date_precision: str | None
    current_snapshot: bool | None
    record_kind: str | None
    temporal_attributes: list[EvidenceAttributeOut]
    limitations: list[str]


class CapturedIdentityValueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    namespace: str
    value: str


class ResearchIdentityCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_label: str
    identifiers: list[CapturedIdentityValueOut]
    aliases: list[CapturedIdentityValueOut]
    declared_match_status: str | None
    status: Literal["unverified_candidate"]


class ResearchSourceEdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_label: str
    collector_source_id: str
    relation: Literal["declared_publisher", "declared_account", "declared_source"]
    declared_name: str | None
    declared_id: str | None
    declared_url: str | None
    status: Literal["unverified_attribution"]


class ResearchSourceRelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_labels: tuple[str, str]
    reasons: list[str]
    shared_parent: str | None
    status: Literal["unverified_relationship"]


class ResearchContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    method_version: str
    timeline: list[ResearchTimelineEntryOut]
    identity_candidates: list[ResearchIdentityCandidateOut]
    source_chains: list[ResearchSourceEdgeOut]
    source_relationships: list[ResearchSourceRelationshipOut]
    limitations: list[str]
