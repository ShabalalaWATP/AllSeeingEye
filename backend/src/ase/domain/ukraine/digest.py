"""The fortnightly Ukraine digest: a bounded model summary of sources already collected.

Nothing here is a verified fact. Every change carries the evidence ids it rests on, and
the stored record keeps only the citations those changes name, never the whole window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# One digest a fortnight, plus an administrator forced refresh.
DIGEST_INTERVAL = timedelta(days=14)
# How many digests are kept so a reader can see the previous ones.
DIGEST_RETENTION = 6
MAX_EVIDENCE_ITEMS = 40
MAX_CITATIONS = 24
MAX_SOURCE_IDS = 40
MAX_PAYLOAD_BYTES = 24_000

ChangeText = Annotated[str, Field(min_length=20, max_length=400)]
NoteText = Annotated[str, Field(min_length=10, max_length=260)]
EvidenceId = Annotated[str, Field(pattern=r"^e[0-9]{1,2}$")]


class DigestPeriod(BaseModel):
    """The fortnight the digest describes, as the model restated it from the pack."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    starts_on: date = Field(alias="from")
    ends_on: date = Field(alias="to")


class DigestChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: ChangeText
    source_ids: list[EvidenceId] = Field(min_length=1, max_length=4)


class DigestStrand(BaseModel):
    """One half of the digest: a short summary and the changes behind it."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    summary: str = Field(min_length=40, max_length=900)
    changes: list[DigestChange] = Field(min_length=2, max_length=5)


class UkraineDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    period: DigestPeriod
    battlefield: DigestStrand
    political: DigestStrand
    watch: list[NoteText] = Field(min_length=2, max_length=4)
    caveats: list[NoteText] = Field(min_length=1, max_length=3)

    def texts(self) -> tuple[str, ...]:
        """Every free-text field, for the mechanical checks run before storing."""
        parts = [*self.watch, *self.caveats]
        for strand in (self.battlefield, self.political):
            parts.append(strand.summary)
            parts.extend(change.text for change in strand.changes)
        return tuple(parts)

    def changes(self) -> tuple[DigestChange, ...]:
        return (*self.battlefield.changes, *self.political.changes)


@dataclass(frozen=True, slots=True)
class DigestCitation:
    """One evidence item a stored digest names, frozen with the assessment."""

    id: str
    kind: str
    source_id: str
    label: str
    dated_on: date | None
    url: str | None


@dataclass(frozen=True, slots=True)
class StoredDigest:
    """A generated digest with its provenance; prompts are never stored."""

    period_start: date
    period_end: date
    generated_at: datetime
    model: str
    digest: UkraineDigest
    citations: tuple[DigestCitation, ...]
    source_ids: tuple[str, ...]
    evidence_items: int
    prompt_tokens: int | None
    completion_tokens: int | None

    def is_due(self, now: datetime) -> bool:
        return now - self.generated_at >= DIGEST_INTERVAL
