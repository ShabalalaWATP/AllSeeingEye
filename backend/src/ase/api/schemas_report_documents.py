"""Typed report comparison response, also generating the frontend contract."""

from pydantic import BaseModel, ConfigDict

from ase.domain.report_documents import ChangeKind


class ReportChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section: str
    path: str
    kind: ChangeKind
    before: str | None
    after: str | None


class ReportComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_version: int
    to_version: int
    changes: list[ReportChangeOut]
