"""Bounded private declarations; clients cannot assert conversion or review results."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.input_declarations import InputPassageDeclaration, InputSourceDate
from ase.domain.source_dates import Calendar, DateRole, SourceDate
from ase.domain.text_transformations import TextTransformation


class InputTextTransformationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["title", "summary"]
    original_text: str = Field(min_length=1, max_length=2000)
    transformed_text: str = Field(min_length=1, max_length=2000)
    kind: Literal["translation", "transliteration"]
    source_language: str = Field(min_length=2, max_length=16)
    target_language: str = Field(min_length=2, max_length=16)
    source_script: str | None = Field(default=None, pattern=r"^[A-Z][a-z]{3}$")
    target_script: str | None = Field(default=None, pattern=r"^[A-Z][a-z]{3}$")
    method: str = Field(min_length=1, max_length=120)


class InputSourceDateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["title", "summary"]
    raw_text: str = Field(min_length=1, max_length=300)
    role: DateRole
    calendar: Calendar


class InputPassageDeclarationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=120)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    transformations: list[InputTextTransformationIn] = Field(default_factory=list, max_length=4)
    source_dates: list[InputSourceDateIn] = Field(default_factory=list, max_length=4)

    def to_domain(self) -> InputPassageDeclaration:
        return InputPassageDeclaration(
            self.event_id,
            self.content_hash,
            tuple(
                TextTransformation(**row.model_dump(), origin="operator")
                for row in self.transformations
            ),
            tuple(InputSourceDate(**row.model_dump()) for row in self.source_dates),
        )


class InputDeclarationsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    declarations: list[InputPassageDeclarationIn] = Field(min_length=1, max_length=8)


class InputDeclarationTargetOut(BaseModel):
    event_id: str
    content_hash: str
    title: str
    summary: str | None
    language: str
    transformations: list[TextTransformation]
    source_dates: list[SourceDate]


class InputDeclarationTargetsOut(BaseModel):
    input_id: UUID
    sha256: str
    expires_at: datetime
    targets: list[InputDeclarationTargetOut] = Field(max_length=200)
