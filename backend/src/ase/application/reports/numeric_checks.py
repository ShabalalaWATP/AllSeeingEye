"""Trace every figure and date in the prose back to the frozen evidence, mechanically.

No model is called. A figure the frozen evidence does not state, does not round to and
cannot be derived from becomes a visible review reason naming the figure and where it
was written. The report text is never altered.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, datetime

from ase.domain.evidence import EvidenceItem
from ase.domain.report_figures import Figure, bounded, derivation_of, figures_in, traceable
from ase.domain.report_quality_rules import DATE_RULE, FIGURE_RULE
from ase.domain.reports import ReportBody, ReportHeader
from ase.domain.validation_types import Finding, Severity

MAX_REPORTED = 12


def prose_passages(body: ReportBody) -> Iterator[tuple[str, str]]:
    """Every model-authored claim about the world, with the place a reader would look.

    The confidence and sourcing statements are excluded: the engine writes counts and
    an instrument share into them, so their figures describe the evidence base itself
    rather than a claim the evidence has to carry.
    """
    for judgement in body.key_judgements:
        yield judgement.id, judgement.statement
        for indicator in judgement.indicators:
            yield judgement.id, indicator
    for theme in body.reporting:
        for index, item in enumerate(theme.items):
            yield f"reporting.{theme.theme or index}", item.text
    for section in body.assessment:
        yield f"assessment.{section.heading or 'section'}", section.text
    for assumption in body.assumptions:
        yield f"assumptions.{assumption.id}", assumption.text
    for index, alternative in enumerate(body.alternative_hypotheses, 1):
        yield f"alternative_hypotheses[{index}]", alternative.text
        yield f"alternative_hypotheses[{index}]", alternative.why_less_likely
    for change in body.indicators_and_warning.changes:
        yield "indicators_and_warning", change
    for index, gap in enumerate(body.gaps, 1):
        yield f"gaps[{index}]", gap.text
    for index, recommendation in enumerate(body.collection_recommendations, 1):
        yield f"collection_recommendations[{index}]", recommendation


def _item_days(item: EvidenceItem) -> Iterator[date]:
    for moment in (item.published_at, item.observed_at, item.captured_at):
        if moment is not None:
            yield moment.date()
    for row in item.source_dates:
        for value in (row.value, row.day_start, row.day_end):
            if isinstance(value, datetime):
                yield value.date()
            elif isinstance(value, date):
                yield value


def evidence_figures(
    evidence: Sequence[EvidenceItem], window: tuple[date, date] | None
) -> tuple[Figure, ...]:
    """Figures the frozen items state, in their text, their attributes and their dates."""
    rows: list[Figure] = []
    for item in evidence:
        for text in (item.title, item.title_en or "", item.summary or "", item.grade_rationale):
            if text:
                rows.extend(figures_in(text, window))
        for attribute in item.attributes:
            if isinstance(attribute.value, bool) or attribute.value is None:
                continue
            rows.extend(figures_in(f"{attribute.value} {attribute.key}", window))
        rows.extend(Figure("date", day.isoformat(), day=day) for day in _item_days(item))
    return bounded(tuple(rows))


def _window(header: ReportHeader) -> tuple[date, date]:
    return header.period_from.date(), max(header.period_to, header.data_cutoff).date()


def _figure_finding(location: str, figure: Figure) -> Finding:
    kinds = {
        "percent": "percentage",
        "percentage_point": "percentage-point figure",
        "currency": "currency amount",
        "count": "figure",
    }
    return Finding(
        FIGURE_RULE,
        Severity.ERROR,
        location,
        f"The {kinds.get(figure.kind, 'figure')} “{figure.describe()}” in "
        f"{location} is not stated by the frozen evidence, is not a rounding of a "
        "stated figure, and cannot be derived from stated figures.",
    )


def _date_finding(location: str, figure: Figure, window: tuple[date, date]) -> Finding:
    return Finding(
        DATE_RULE,
        Severity.ERROR,
        location,
        f"The date “{figure.describe()}” in {location} is not carried by any "
        f"frozen source and falls outside the reporting period "
        f"{window[0].isoformat()} to {window[1].isoformat()}.",
    )


def check_figures(
    body: ReportBody, header: ReportHeader, evidence: Sequence[EvidenceItem]
) -> tuple[Finding, ...]:
    """Report untraceable figures and dates; an empty result means every figure matched."""
    window = _window(header)
    known = evidence_figures(evidence, window)
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for location, text in prose_passages(body):
        if not text.strip():
            continue
        for figure in figures_in(text, window):
            key = (location, figure.describe())
            if key in seen or traceable(figure, known):
                continue
            seen.add(key)
            if figure.kind == "date":
                if window[0] <= (figure.day or window[0]) <= window[1]:
                    continue
                findings.append(_date_finding(location, figure, window))
            elif not derivation_of(figure, known):
                findings.append(_figure_finding(location, figure))
    if len(findings) > MAX_REPORTED:
        remaining = len(findings) - MAX_REPORTED
        findings = [
            *findings[:MAX_REPORTED],
            Finding(
                FIGURE_RULE,
                Severity.ERROR,
                "report",
                f"A further {remaining} figure(s) in the prose could not be traced to the "
                "frozen evidence; the report needs a numerical review.",
            ),
        ]
    return tuple(findings)
