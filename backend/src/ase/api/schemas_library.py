"""Strict private library input and current visible report summaries."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_reports import ReportSummaryOut
from ase.domain.research_library import LibraryPage, LibraryPreference


class LibraryPreferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    favourite: bool = False
    tags: list[str] = Field(default_factory=list, max_length=12)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_preferences(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> LibraryPreference:
        return LibraryPreference(self.favourite, tuple(self.tags), self.note)


class LibraryPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    favourite: bool
    tags: list[str]
    note: str | None
    updated_at: datetime | None


class LibraryItemOut(BaseModel):
    report: ReportSummaryOut
    preference: LibraryPreferenceOut


class LibraryPageOut(BaseModel):
    items: list[LibraryItemOut]
    total: int
    offset: int
    limit: int

    @classmethod
    def build(cls, page: LibraryPage) -> Self:
        return cls(
            items=[
                LibraryItemOut(
                    report=ReportSummaryOut.from_record(item.report),
                    preference=LibraryPreferenceOut.model_validate(item.preference),
                )
                for item in page.items
            ],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )
