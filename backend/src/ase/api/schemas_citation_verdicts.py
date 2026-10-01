"""Citation verdict input excludes reviewer identity, scope and times; the server sets them."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.reports.citation_verdicts import CitationVerdictInput, CitationVerdictList
from ase.domain.citation_verdicts import (
    HUMAN_OPINION_NOTE,
    MAX_VERDICT_NOTE,
    CitationVerdict,
    CitationVerdictValue,
)

AnchorText = Annotated[str, Field(min_length=1, max_length=200)]


class CitationVerdictIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judgement_id: AnchorText
    label: AnchorText
    relation: Literal["supporting", "contradicting"]
    verdict: CitationVerdictValue
    note: Annotated[str, Field(min_length=1, max_length=MAX_VERDICT_NOTE)] | None = None

    def to_input(self) -> CitationVerdictInput:
        note = self.note.strip() if self.note is not None else None
        return CitationVerdictInput(
            self.judgement_id, self.label, self.relation, self.verdict, note or None
        )


class CitationVerdictOut(BaseModel):
    id: UUID
    report_id: UUID
    report_version_id: UUID
    version_number: int
    judgement_id: str
    label: str
    relation: Literal["supporting", "contradicting"]
    verdict: CitationVerdictValue
    note: str | None
    reviewer_id: UUID
    team_id: UUID | None
    recorded_at: datetime

    @classmethod
    def from_verdict(cls, value: CitationVerdict) -> Self:
        return cls(
            id=value.id,
            report_id=value.report_id,
            report_version_id=value.report_version_id,
            version_number=value.version_number,
            judgement_id=value.anchor.judgement_id,
            label=value.anchor.label,
            relation=value.anchor.relation,
            verdict=value.verdict,
            note=value.note,
            reviewer_id=value.reviewer_id,
            team_id=value.team_id,
            recorded_at=value.recorded_at,
        )


class CitationVerdictListOut(BaseModel):
    verdicts: list[CitationVerdictOut]
    can_record: bool
    limit: int
    note_limit: int = MAX_VERDICT_NOTE
    notice: str = HUMAN_OPINION_NOTE

    @classmethod
    def from_list(cls, value: CitationVerdictList) -> Self:
        return cls(
            verdicts=[CitationVerdictOut.from_verdict(row) for row in value.verdicts],
            can_record=value.can_record,
            limit=value.limit,
        )
