"""Ukraine digest contract: the model's words, the evidence it named and how it was made."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.application.ukraine_digest import DigestStatus, DigestView
from ase.domain.ukraine.digest import DigestStrand, StoredDigest


class DigestChangeOut(BaseModel):
    text: str
    source_ids: list[str]


class DigestStrandOut(BaseModel):
    summary: str
    changes: list[DigestChangeOut]

    @classmethod
    def from_strand(cls, strand: DigestStrand) -> Self:
        return cls(
            summary=strand.summary,
            changes=[
                DigestChangeOut(text=change.text, source_ids=list(change.source_ids))
                for change in strand.changes
            ],
        )


class DigestCitationOut(BaseModel):
    id: str
    kind: str
    source_id: str
    label: str
    dated_on: date | None
    url: str | None


class DigestEntryOut(BaseModel):
    """One stored digest with its provenance; the prompt is never kept or returned."""

    period_start: date
    period_end: date
    generated_at: datetime
    model: str
    evidence_items: int = Field(ge=0)
    source_ids: list[str]
    prompt_tokens: int | None
    completion_tokens: int | None
    battlefield: DigestStrandOut
    political: DigestStrandOut
    watch: list[str]
    caveats: list[str]
    citations: list[DigestCitationOut]

    @classmethod
    def from_stored(cls, stored: StoredDigest) -> Self:
        return cls(
            period_start=stored.period_start,
            period_end=stored.period_end,
            generated_at=stored.generated_at,
            model=stored.model,
            evidence_items=stored.evidence_items,
            source_ids=list(stored.source_ids),
            prompt_tokens=stored.prompt_tokens,
            completion_tokens=stored.completion_tokens,
            battlefield=DigestStrandOut.from_strand(stored.digest.battlefield),
            political=DigestStrandOut.from_strand(stored.digest.political),
            watch=list(stored.digest.watch),
            caveats=list(stored.digest.caveats),
            citations=[
                DigestCitationOut(
                    id=item.id,
                    kind=item.kind,
                    source_id=item.source_id,
                    label=item.label,
                    dated_on=item.dated_on,
                    url=item.url,
                )
                for item in stored.citations
            ],
        )


class UkraineDigestOut(BaseModel):
    status: DigestStatus
    reason: str | None
    stale: bool
    generating: bool
    interval_days: int = Field(ge=1)
    latest: DigestEntryOut | None
    previous: list[DigestEntryOut]

    @classmethod
    def from_view(cls, view: DigestView) -> Self:
        return cls(
            status=view.status,
            reason=view.reason,
            stale=view.stale,
            generating=view.generating,
            interval_days=view.interval_days,
            latest=(DigestEntryOut.from_stored(view.latest) if view.latest is not None else None),
            previous=[DigestEntryOut.from_stored(item) for item in view.previous],
        )
