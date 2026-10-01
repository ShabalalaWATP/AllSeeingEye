"""Response shape for a source track record: counts and dated lists, never a score."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

SavedStatus = Literal["ready", "needs_review", "failed"]


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TrackRecordRolesOut(_Out):
    supporting_judgements: int
    contradicting_judgements: int
    items_cited_elsewhere: int
    items_not_cited: int


class TrackRecordStatusesOut(_Out):
    ready: int
    needs_review: int
    failed: int


class TrackRecordValueOut(_Out):
    value: str
    items: int


class TrackRecordEntryOut(_Out):
    report_id: UUID
    title: str
    version_number: int
    status: SavedStatus
    saved_at: datetime
    items: int
    supporting_judgements: int
    contradicting_judgements: int
    grades: list[str]


class TrackRecordReviewOut(_Out):
    kind: Literal["reliability", "credibility", "authenticity"]
    decision: str
    recorded_at: datetime
    report_id: UUID
    team_scoped: bool


class CitationVerdictsOut(_Out):
    available: bool
    note: str
    citations: int
    citations_with_verdicts: int
    current_verdicts: int
    superseded_verdicts: int
    supports: int
    partly_supports: int
    does_not_support: int
    cannot_tell: int
    reviewers: int


class SourceTrackRecordOut(_Out):
    source_id: str
    report_bound: int
    reports_considered: int
    visible_reports: int
    reports_citing: int
    frozen_items: int
    roles: TrackRecordRolesOut
    reports_by_status: TrackRecordStatusesOut
    judgements_by_status: TrackRecordStatusesOut
    reliability: list[TrackRecordValueOut]
    credibility: list[TrackRecordValueOut]
    entries: list[TrackRecordEntryOut]
    entries_total: int
    reviews: list[TrackRecordReviewOut]
    reviews_total: int
    citation_verdicts: CitationVerdictsOut
