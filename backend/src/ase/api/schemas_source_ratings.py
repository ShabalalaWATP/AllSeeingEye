"""Typed qualitative source-rating context, with unknowns distinct from editorial grades."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.domain.events import Reliability
from ase.domain.source_rating_catalog import ProvenanceRole


class SourceRatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_version: str
    status: Literal["editorial", "unassessed"]
    assessed_grade: Reliability | None
    basis: str
    scope: str
    limitations: list[str]
    provenance_role: ProvenanceRole
    publisher_reliability_assessed: bool
    reviewed_at: datetime | None
