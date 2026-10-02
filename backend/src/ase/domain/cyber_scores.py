"""Optional source scores with distinct probability and severity semantics."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EpssScore:
    probability: float
    percentile: float
    date: str


@dataclass(frozen=True, slots=True)
class CvssScore:
    base_score: float
    version: str
    vector: str
    source: str
    updated_at: str
