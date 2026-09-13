"""Reference notes contract: public background keyed by a broadcast identifier."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.domain.reference import ReferenceEntry, ReferenceKind


class ReferenceLinkOut(BaseModel):
    label: str
    url: str


class ReferenceEntryOut(BaseModel):
    kind: ReferenceKind
    key: str
    name: str
    description: str
    detail: str
    links: list[ReferenceLinkOut] = Field(max_length=4)
    provenance: str

    @classmethod
    def from_entry(cls, entry: ReferenceEntry) -> Self:
        return cls(
            kind=entry.kind,
            key=entry.key,
            name=entry.name,
            description=entry.description,
            detail=entry.detail,
            links=[ReferenceLinkOut(label=link.label, url=link.url) for link in entry.links],
            provenance=entry.provenance,
        )


class ReferenceLookupOut(BaseModel):
    items: list[ReferenceEntryOut] = Field(max_length=50)
    retrieved_at: datetime
    caveat: str
