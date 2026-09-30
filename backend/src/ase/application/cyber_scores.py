"""Do not turn absent, partial or malformed public scores into zero."""

import math
from collections.abc import Mapping

from ase.domain.cyber_scores import CvssScore, EpssScore
from ase.domain.events import JsonScalar


def _number(value: JsonScalar, maximum: float) -> float | None:
    if type(value) not in (int, float) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) and 0 <= value <= maximum else None


def epss_score(values: Mapping[str, JsonScalar]) -> EpssScore | None:
    probability = _number(values.get("epss_probability"), 1)
    percentile = _number(values.get("epss_percentile"), 1)
    date = values.get("epss_date")
    if probability is None or percentile is None or not isinstance(date, str) or not date:
        return None
    return EpssScore(probability, percentile, date)


def cvss_score(values: Mapping[str, JsonScalar]) -> CvssScore | None:
    score = _number(values.get("cvss_score"), 10)
    version, vector = values.get("cvss_version"), values.get("cvss_vector")
    source, date = values.get("cvss_source"), values.get("cvss_date")
    if (
        score is None
        or not isinstance(version, str)
        or not isinstance(vector, str)
        or not isinstance(source, str)
        or not isinstance(date, str)
    ):
        return None
    return CvssScore(score, version, vector, source, date)
