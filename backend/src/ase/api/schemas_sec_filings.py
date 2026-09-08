"""Explicit company filing selection without client-supplied fetch URLs."""

from dataclasses import asdict
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.sec_filings import SecFilingChoice


class SecFilingsSearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cik: str = Field(pattern=r"^[0-9]{1,10}$")
    since: date
    until: date
    archive_page: int = Field(default=0, strict=True, ge=0, le=50)
    offset: int = Field(default=0, strict=True, ge=0, le=9980, multiple_of=20)


class SecFilingChoiceOut(BaseModel):
    selection_id: UUID
    cik: str
    accession: str
    primary_document: str
    form: str
    filing_date: date
    company_name: str
    expires_at: datetime

    @classmethod
    def from_choice(cls, value: SecFilingChoice) -> "SecFilingChoiceOut":
        return cls.model_validate(
            {
                **asdict(value.filing),
                "selection_id": value.selection_id,
                "expires_at": value.expires_at,
            }
        )


class SecFilingsPageOut(BaseModel):
    items: list[SecFilingChoiceOut]
    archive_page: int
    archive_pages: int
    offset: int
    next_offset: int | None
    limitations: list[str]
