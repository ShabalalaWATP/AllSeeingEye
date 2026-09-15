"""Fixed dispatch from validated specifications to exact domain calculators."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ase.application.analysis.spec import AnalysisSpec
from ase.domain.quantitative_calculations import (
    AlignedMethod,
    Formula,
    QuantitativeResult,
    RollingMethod,
    absolute_change,
    aligned_period_comparison,
    indexed_series,
    percentage_change,
    rate,
    rolling_summary,
)
from ase.domain.quantitative_observations import (
    ObservationPeriod,
    QuantitativeObservation,
    QuantitativeSeries,
)

MAX_SERIES = 16


class AuthorisedQuantitativeSet:
    """A small caller-authorised input snapshot; this class performs no retrieval."""

    __slots__ = ("_observations", "_series")

    def __init__(self, series: tuple[QuantitativeSeries, ...]) -> None:
        if type(series) is not tuple or not 1 <= len(series) <= MAX_SERIES:
            raise ValueError("Analysis needs one to 16 authorised series")
        by_series: dict[str, QuantitativeSeries] = {}
        by_observation: dict[str, QuantitativeObservation] = {}
        for item in series:
            if not isinstance(item, QuantitativeSeries):
                raise ValueError("Analysis requires typed source series")
            identity = item.observations[0].series_id
            if identity in by_series:
                raise ValueError("Authorised series identities must be unique")
            by_series[identity] = item
            for observation in item.observations:
                if observation.id in by_observation:
                    raise ValueError("Authorised observation identities must be unique")
                by_observation[observation.id] = observation
        self._series: Mapping[str, QuantitativeSeries] = MappingProxyType(by_series)
        self._observations: Mapping[str, QuantitativeObservation] = MappingProxyType(by_observation)

    def series(self, identity: str) -> QuantitativeSeries:
        try:
            return self._series[identity]
        except KeyError as error:
            raise ValueError("Series is unavailable in the authorised analysis snapshot") from error

    def observation(self, identity: str) -> QuantitativeObservation:
        try:
            return self._observations[identity]
        except KeyError as error:
            raise ValueError(
                "Observation is unavailable in the authorised analysis snapshot"
            ) from error


@dataclass(frozen=True, slots=True)
class AnalysisExecution:
    """Validated outputs retain each calculator's exact formula and source receipt."""

    operation: Formula
    schema_version: int
    results: tuple[QuantitativeResult, ...]
    evidence_ids: tuple[str, ...]
    source_ids: tuple[str, ...]


def _change(
    spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet
) -> tuple[QuantitativeResult, ...]:
    earlier, later = (inputs.observation(identity) for identity in spec.observation_ids)
    calculator = absolute_change if spec.operation is Formula.ABSOLUTE_CHANGE else percentage_change
    return (calculator(earlier, later),)


def _rate(spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet) -> tuple[QuantitativeResult, ...]:
    numerator, denominator = (inputs.observation(identity) for identity in spec.observation_ids)
    if spec.scale is None:
        raise ValueError("Rate scale is required")
    return (rate(numerator, denominator, scale=spec.scale),)


def _index(spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet) -> tuple[QuantitativeResult, ...]:
    series = inputs.series(spec.series_ids[0])
    if spec.base_period_start is None:
        raise ValueError("Index base period is required")
    base = ObservationPeriod(spec.base_period_start, series.observations[0].period.frequency)
    return indexed_series(series, base)


def _rolling(
    spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet
) -> tuple[QuantitativeResult, ...]:
    if spec.window_length is None:
        raise ValueError("Rolling window length is required")
    method = RollingMethod.SUM if spec.operation is Formula.ROLLING_SUM else RollingMethod.MEAN
    return rolling_summary(
        inputs.series(spec.series_ids[0]), window=spec.window_length, method=method
    )


def _aligned(
    spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet
) -> tuple[QuantitativeResult, ...]:
    method = (
        AlignedMethod.ABSOLUTE
        if spec.operation is Formula.ALIGNED_ABSOLUTE
        else AlignedMethod.PERCENTAGE
    )
    return aligned_period_comparison(
        inputs.series(spec.series_ids[0]), inputs.series(spec.series_ids[1]), method=method
    )


Tool = Callable[[AnalysisSpec, AuthorisedQuantitativeSet], tuple[QuantitativeResult, ...]]
TOOLS: Mapping[Formula, Tool] = MappingProxyType(
    {
        Formula.ABSOLUTE_CHANGE: _change,
        Formula.PERCENTAGE_CHANGE: _change,
        Formula.INDEX_BASE_100: _index,
        Formula.ROLLING_SUM: _rolling,
        Formula.ROLLING_MEAN: _rolling,
        Formula.RATE: _rate,
        Formula.ALIGNED_ABSOLUTE: _aligned,
        Formula.ALIGNED_PERCENTAGE: _aligned,
    }
)


def execute_analysis(spec: AnalysisSpec, inputs: AuthorisedQuantitativeSet) -> AnalysisExecution:
    """Execute one allowlisted calculation without model-supplied source values."""

    if not isinstance(spec, AnalysisSpec) or not isinstance(inputs, AuthorisedQuantitativeSet):
        raise ValueError("Validated specification and authorised inputs are required")
    results = TOOLS[spec.operation](spec, inputs)
    evidence_ids = tuple(
        dict.fromkeys(item.evidence_id for result in results for item in result.receipt.inputs)
    )
    source_ids = tuple(
        dict.fromkeys(item.source_id for result in results for item in result.receipt.inputs)
    )
    return AnalysisExecution(spec.operation, spec.schema_version, results, evidence_ids, source_ids)
