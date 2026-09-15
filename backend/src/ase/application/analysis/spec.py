"""The only model-facing quantitative tool specification.

The model selects an allowlisted calculation and authorised input identities. It
cannot submit observations, calculated values, executable code or network targets.
"""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ase.domain.quantitative_calculations import Formula

SPEC_VERSION = 1
MAX_SPEC_BYTES = 4096


class AnalysisSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    operation: Formula
    observation_ids: tuple[str, ...] = ()
    series_ids: tuple[str, ...] = ()
    base_period_start: date | None = None
    window_length: int | None = None
    scale: int | None = None

    @field_validator("observation_ids", "series_ids")
    @classmethod
    def valid_identifiers(cls, identifiers: tuple[str, ...]) -> tuple[str, ...]:
        if (
            len(identifiers) > 2
            or len(identifiers) != len(set(identifiers))
            or any(not value or value != value.strip() or len(value) > 160 for value in identifiers)
        ):
            raise ValueError("Analysis input identities must be distinct, bounded and exact")
        return identifiers

    @model_validator(mode="after")
    def exact_operation_parameters(self) -> Self:
        change = {Formula.ABSOLUTE_CHANGE, Formula.PERCENTAGE_CHANGE}
        rolling = {Formula.ROLLING_SUM, Formula.ROLLING_MEAN}
        aligned = {Formula.ALIGNED_ABSOLUTE, Formula.ALIGNED_PERCENTAGE}
        if self.operation in change:
            valid = len(self.observation_ids) == 2 and not self.series_ids
            valid &= self.base_period_start is None and self.window_length is None
            valid &= self.scale is None
        elif self.operation is Formula.RATE:
            valid = len(self.observation_ids) == 2 and not self.series_ids
            valid &= self.base_period_start is None and self.window_length is None
            valid &= self.scale in (1, 100, 1_000, 100_000) and type(self.scale) is int
        elif self.operation is Formula.INDEX_BASE_100:
            valid = not self.observation_ids and len(self.series_ids) == 1
            valid &= self.base_period_start is not None
            valid &= self.window_length is None and self.scale is None
        elif self.operation in rolling:
            valid = not self.observation_ids and len(self.series_ids) == 1
            valid &= self.base_period_start is None and self.scale is None
            valid &= type(self.window_length) is int and 2 <= self.window_length <= 24
        elif self.operation in aligned:
            valid = not self.observation_ids and len(self.series_ids) == 2
            valid &= self.base_period_start is None and self.window_length is None
            valid &= self.scale is None
        else:
            valid = False
        if not valid:
            raise ValueError("Analysis parameters do not match the allowlisted operation")
        return self


def parse_analysis_spec(payload: str) -> AnalysisSpec:
    """Validate one bounded JSON proposal before it reaches any source value."""

    if type(payload) is not str or not 0 < len(payload.encode("utf-8")) <= MAX_SPEC_BYTES:
        raise ValueError("Analysis specification must be bounded JSON")
    return AnalysisSpec.model_validate_json(payload)
