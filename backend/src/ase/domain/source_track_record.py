"""Counts and dated lists of how one source was used in saved reports. No score is derived.

The population is the caller's latest visible reports, bounded, each read at its latest
saved version. Counts describe frozen citations; they are not a reliability measure.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from ase.domain.citation_verdicts import HUMAN_OPINION_NOTE, tally_verdicts
from ase.domain.reports import ReportStatus

if TYPE_CHECKING:
    from ase.domain.citation_verdicts import CitationVerdict
    from ase.domain.evidence import EvidenceItem
    from ase.domain.reports import ReportBody
    from ase.domain.source_reviews import SourceReviewRevision

MAX_TRACK_RECORD_REPORTS = 1_000
MAX_TRACK_RECORD_ENTRIES = 25
MAX_TRACK_RECORD_REVIEWS = 25
MAX_REVIEW_SCAN = 2_000
MAX_VERDICT_SCAN = 5_000
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z")
CITATION_VERDICTS_NOTE = (
    f"{HUMAN_OPINION_NOTE} Counts cover each reviewer's latest verdict on citations of this "
    "source in the latest saved version of each considered report. A citation without a "
    "verdict has not passed any check."
)


def valid_source_id(value: str) -> bool:
    """Plain catalogue identifiers only, which JSON storage never escapes."""
    return type(value) is str and _SOURCE_ID.match(value) is not None


@dataclass(frozen=True, slots=True)
class CitedVersion:
    """A report's latest saved version that froze at least one item from the source."""

    report_id: UUID
    title: str
    version_number: int
    status: ReportStatus
    saved_at: datetime
    body: ReportBody
    items: tuple[EvidenceItem, ...]


@dataclass(frozen=True, slots=True)
class TrackRecordPopulation:
    bound: int
    visible_reports: int
    report_ids: frozenset[UUID]
    versions: tuple[CitedVersion, ...]


@dataclass(frozen=True, slots=True)
class RoleCounts:
    supporting_judgements: int
    contradicting_judgements: int
    items_cited_elsewhere: int
    items_not_cited: int


@dataclass(frozen=True, slots=True)
class StatusCounts:
    ready: int
    needs_review: int
    failed: int

    @classmethod
    def of(cls, statuses: Iterable[ReportStatus]) -> StatusCounts:
        counts = Counter(statuses)
        return cls(
            counts[ReportStatus.READY],
            counts[ReportStatus.NEEDS_REVIEW],
            counts[ReportStatus.FAILED],
        )


@dataclass(frozen=True, slots=True)
class ValueCount:
    value: str
    items: int


@dataclass(frozen=True, slots=True)
class TrackRecordEntry:
    report_id: UUID
    title: str
    version_number: int
    status: ReportStatus
    saved_at: datetime
    items: int
    supporting_judgements: int
    contradicting_judgements: int
    grades: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewEntry:
    kind: str
    decision: str
    recorded_at: datetime
    report_id: UUID
    team_scoped: bool


@dataclass(frozen=True, slots=True)
class CitationVerdicts:
    """Current human verdicts out of this source's key-judgement citations. No score."""

    available: bool
    note: str
    citations: int = 0
    citations_with_verdicts: int = 0
    current_verdicts: int = 0
    superseded_verdicts: int = 0
    supports: int = 0
    partly_supports: int = 0
    does_not_support: int = 0
    cannot_tell: int = 0
    reviewers: int = 0


@dataclass(frozen=True, slots=True)
class SourceTrackRecord:
    source_id: str
    report_bound: int
    reports_considered: int
    visible_reports: int
    reports_citing: int
    frozen_items: int
    roles: RoleCounts
    reports_by_status: StatusCounts
    judgements_by_status: StatusCounts
    reliability: tuple[ValueCount, ...]
    credibility: tuple[ValueCount, ...]
    entries: tuple[TrackRecordEntry, ...]
    entries_total: int
    reviews: tuple[ReviewEntry, ...]
    reviews_total: int
    citation_verdicts: CitationVerdicts


@dataclass(frozen=True, slots=True)
class _VersionRoles:
    supporting: int
    contradicting: int
    elsewhere: int
    uncited: int


def _roles(version: CitedVersion) -> _VersionRoles:
    labels = {item.label for item in version.items}
    judgements = version.body.key_judgements
    supporting = sum(bool(labels & set(row.supporting_evidence)) for row in judgements)
    contradicting = sum(bool(labels & set(row.contradicting_evidence)) for row in judgements)
    in_judgements = {
        label
        for row in judgements
        for label in (*row.supporting_evidence, *row.contradicting_evidence)
    }
    cited = version.body.cited_labels()
    elsewhere = sum(1 for label in labels if label in cited and label not in in_judgements)
    return _VersionRoles(supporting, contradicting, elsewhere, len(labels - cited))


def _citing_judgements(version: CitedVersion) -> int:
    labels = {item.label for item in version.items}
    return sum(
        bool(labels & {*row.supporting_evidence, *row.contradicting_evidence})
        for row in version.body.key_judgements
    )


def _values(values: Iterable[str]) -> tuple[ValueCount, ...]:
    return tuple(ValueCount(value, count) for value, count in sorted(Counter(values).items()))


def _decision(review: SourceReviewRevision) -> str:
    if review.reliability is not None:
        return review.reliability.value
    if review.credibility is not None:
        return str(review.credibility.value)
    if review.authenticity is not None:
        return review.authenticity.status.value
    return "recorded"


def _reviews(
    source_id: str, report_ids: frozenset[UUID], reviews: Sequence[SourceReviewRevision]
) -> list[ReviewEntry]:
    rows = [
        ReviewEntry(
            review.kind.value,
            _decision(review),
            review.review.recorded_at,
            review.target.report_id,
            review.scope.team_id is not None,
        )
        for review in reviews
        if review.target.source_id == source_id and review.target.report_id in report_ids
    ]
    return sorted(rows, key=lambda row: (row.recorded_at, str(row.report_id)), reverse=True)


def _verdicts(
    versions: Sequence[CitedVersion], verdicts: Sequence[CitationVerdict]
) -> CitationVerdicts:
    labels = {
        (row.report_id, row.version_number): {item.label for item in row.items} for row in versions
    }
    citations = sum(
        label in labels[(row.report_id, row.version_number)]
        for row in versions
        for judgement in row.body.key_judgements
        for label in (*judgement.supporting_evidence, *judgement.contradicting_evidence)
    )
    tally = tally_verdicts(
        row
        for row in verdicts
        if row.anchor.label in labels.get((row.report_id, row.version_number), set())
    )
    return CitationVerdicts(
        True,
        CITATION_VERDICTS_NOTE,
        citations,
        tally.citations_with_verdicts,
        tally.current_verdicts,
        tally.superseded_verdicts,
        tally.supports,
        tally.partly_supports,
        tally.does_not_support,
        tally.cannot_tell,
        tally.reviewers,
    )


def build_track_record(
    source_id: str,
    population: TrackRecordPopulation,
    reviews: Sequence[SourceReviewRevision] = (),
    verdicts: Sequence[CitationVerdict] = (),
) -> SourceTrackRecord:
    versions = sorted(
        (row for row in population.versions if row.report_id in population.report_ids),
        key=lambda row: (row.saved_at, str(row.report_id)),
        reverse=True,
    )
    roles = [_roles(row) for row in versions]
    items = [item for row in versions for item in row.items]
    entries = tuple(
        TrackRecordEntry(
            row.report_id,
            row.title,
            row.version_number,
            row.status,
            row.saved_at,
            len(row.items),
            role.supporting,
            role.contradicting,
            tuple(item.grade for item in row.items),
        )
        for row, role in zip(versions, roles, strict=True)
    )
    review_rows = _reviews(source_id, population.report_ids, reviews)
    return SourceTrackRecord(
        source_id=source_id,
        report_bound=population.bound,
        reports_considered=len(population.report_ids),
        visible_reports=population.visible_reports,
        reports_citing=len(versions),
        frozen_items=len(items),
        roles=RoleCounts(
            sum(row.supporting for row in roles),
            sum(row.contradicting for row in roles),
            sum(row.elsewhere for row in roles),
            sum(row.uncited for row in roles),
        ),
        reports_by_status=StatusCounts.of(row.status for row in versions),
        judgements_by_status=StatusCounts.of(
            row.status for row in versions for _ in range(_citing_judgements(row))
        ),
        reliability=_values(item.reliability for item in items),
        credibility=_values(str(item.credibility) for item in items),
        entries=entries[:MAX_TRACK_RECORD_ENTRIES],
        entries_total=len(entries),
        reviews=tuple(review_rows[:MAX_TRACK_RECORD_REVIEWS]),
        reviews_total=len(review_rows),
        citation_verdicts=_verdicts(versions, verdicts),
    )
