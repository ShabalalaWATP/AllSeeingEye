"""Human verdicts on whether one model citation supports its saved judgement.

A verdict is a reviewer's opinion about one citation in one exact saved report version:
the judgement id, the evidence label and the relation the model assigned. Verdicts are
append-only. A later verdict by the same reviewer on the same citation supersedes the
earlier one for counting, while the history is retained. Verdicts never change the
frozen report, its grades, its confidence or its citation checks.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    from ase.domain.reports import ReportBody

MAX_VERDICT_NOTE = 300
MAX_VERSION_VERDICTS = 500
MAX_CITATION_VERDICTS = 50
MAX_ANCHOR_TEXT = 200
VERDICT_DATASET = "ase-report-citation-verdicts-v1"
HUMAN_OPINION_NOTE = (
    "Citation verdicts are human opinions recorded by reviewers. They are not ground "
    "truth, and they never change the frozen report, its grades or its confidence."
)
Relation = Literal["supporting", "contradicting"]
RELATIONS: tuple[Relation, ...] = ("supporting", "contradicting")


class CitationVerdictValue(StrEnum):
    SUPPORTS = "supports"
    PARTLY_SUPPORTS = "partly_supports"
    DOES_NOT_SUPPORT = "does_not_support"
    CANNOT_TELL = "cannot_tell"


def _text(value: object, maximum: int) -> str:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("Citation verdict anchors must be short, non-empty text.")
    return value


@dataclass(frozen=True, slots=True)
class CitationAnchor:
    """One citation of one saved judgement, exactly as the model assigned it."""

    judgement_id: str
    label: str
    relation: Relation

    def __post_init__(self) -> None:
        _text(self.judgement_id, MAX_ANCHOR_TEXT)
        _text(self.label, MAX_ANCHOR_TEXT)
        if self.relation not in RELATIONS:
            raise ValueError("A citation relation is supporting or contradicting.")


@dataclass(frozen=True, slots=True)
class CitationVerdict:
    id: UUID
    report_id: UUID
    report_version_id: UUID
    version_number: int
    anchor: CitationAnchor
    verdict: CitationVerdictValue
    note: str | None
    owner_id: UUID
    team_id: UUID | None
    reviewer_id: UUID
    recorded_at: datetime

    def __post_init__(self) -> None:
        for value in (self.id, self.report_id, self.report_version_id, self.owner_id):
            if not isinstance(value, UUID):
                raise ValueError("Citation verdicts require exact identities.")
        if not isinstance(self.reviewer_id, UUID) or (
            self.team_id is not None and not isinstance(self.team_id, UUID)
        ):
            raise ValueError("Citation verdicts require an explicit reviewer and scope.")
        if type(self.version_number) is not int or self.version_number < 1:
            raise ValueError("Citation verdicts require an exact saved version number.")
        if not isinstance(self.anchor, CitationAnchor) or not isinstance(
            self.verdict, CitationVerdictValue
        ):
            raise ValueError("Citation verdicts require a cited anchor and a verdict value.")
        if self.note is not None and (
            type(self.note) is not str or not self.note.strip() or len(self.note) > MAX_VERDICT_NOTE
        ):
            raise ValueError("A verdict note is at most 300 characters.")
        if self.recorded_at.tzinfo is None:
            raise ValueError("Citation verdict times must be timezone aware.")


def cited_anchor(body: ReportBody, judgement_id: str, label: str, relation: str) -> CitationAnchor:
    """The anchor exists only if the frozen judgement cites the label in that relation."""
    matching = [row for row in body.key_judgements if row.id == judgement_id]
    if len(matching) != 1:
        raise ValueError("Choose one saved judgement.")
    judgement = matching[0]
    cited = (
        judgement.supporting_evidence
        if relation == "supporting"
        else judgement.contradicting_evidence
        if relation == "contradicting"
        else ()
    )
    if label not in cited:
        raise ValueError("Choose a citation recorded on the saved judgement.")
    return CitationAnchor(
        judgement_id, label, "supporting" if relation == "supporting" else "contradicting"
    )


def current_verdicts(verdicts: Iterable[CitationVerdict]) -> tuple[CitationVerdict, ...]:
    """Each reviewer's latest verdict on each citation of each exact version."""
    latest: dict[tuple[UUID, CitationAnchor, UUID], CitationVerdict] = {}
    for row in sorted(verdicts, key=lambda item: (item.recorded_at, str(item.id))):
        latest[(row.report_version_id, row.anchor, row.reviewer_id)] = row
    return tuple(sorted(latest.values(), key=lambda item: (item.recorded_at, str(item.id))))


@dataclass(frozen=True, slots=True)
class VerdictTally:
    """Counts of current verdicts with their denominators. Never a single accuracy figure."""

    supports: int
    partly_supports: int
    does_not_support: int
    cannot_tell: int
    current_verdicts: int
    superseded_verdicts: int
    citations_with_verdicts: int
    reviewers: int


def tally_verdicts(verdicts: Iterable[CitationVerdict]) -> VerdictTally:
    rows = tuple(verdicts)
    current = current_verdicts(rows)
    counts = Counter(row.verdict for row in current)
    return VerdictTally(
        supports=counts[CitationVerdictValue.SUPPORTS],
        partly_supports=counts[CitationVerdictValue.PARTLY_SUPPORTS],
        does_not_support=counts[CitationVerdictValue.DOES_NOT_SUPPORT],
        cannot_tell=counts[CitationVerdictValue.CANNOT_TELL],
        current_verdicts=len(current),
        superseded_verdicts=len(rows) - len(current),
        citations_with_verdicts=len({(row.report_version_id, row.anchor) for row in current}),
        reviewers=len({row.reviewer_id for row in current}),
    )
