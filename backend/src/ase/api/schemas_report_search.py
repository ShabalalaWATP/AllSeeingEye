"""Semantic search API, with no provider address, credential or raw vector read-back."""

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_reports import ReportSummaryOut


class ReportSearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=20)


class ReportSearchStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    available: bool
    indexed: int
    total: int
    limit: int
    batch_size: int


class ReportSearchHitOut(BaseModel):
    report: ReportSummaryOut
    score: float


class ReportSearchOut(BaseModel):
    items: list[ReportSearchHitOut]
    indexed: int
    total: int
