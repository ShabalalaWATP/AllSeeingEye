"""Administrator scorecard of saved report outcomes and report jobs: counts, never a score.

Two populations are kept apart and never summed: saved report versions (each counted
once, by its saved status) and report jobs (each counted once, by its job status, so
failed jobs that never saved a version remain visible). Each is bounded to the most
recent rows in a time window. A missing dimension is grouped as `not_recorded`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ase.domain.citation_verdicts import HUMAN_OPINION_NOTE, CitationVerdict, tally_verdicts

MAX_QUALITY_VERSIONS = 1_000
MAX_QUALITY_JOBS = 1_000
QUALITY_WINDOWS = (7, 30, 90, 365)
DEFAULT_QUALITY_WINDOW = 90
NOT_RECORDED = "not_recorded"
TOP_FINDINGS = 5
TOP_FAILURE_CODES = 5
MAX_LABEL = 120
MAX_QUALITY_VERDICTS = 5_000
CITATION_CHECKS_NOTE = (
    f"{HUMAN_OPINION_NOTE} Counts cover each reviewer's latest verdict among the newest "
    "verdicts recorded in the window. A citation without a verdict has not passed any check."
)
UNSUCCESSFUL_RECEIPTS = frozenset(
    {"failed", "timed_out", "budget_exhausted", "not_collected", "unsupported"}
)


@dataclass(frozen=True, slots=True)
class VersionOutcome:
    status: str
    template: str | None
    depth: str | None
    connection: str | None
    findings: tuple[tuple[str, str], ...]
    receipts: tuple[str, ...] | None
    prompt_tokens: int | None
    completion_tokens: int | None


@dataclass(frozen=True, slots=True)
class JobOutcome:
    status: str
    template: str | None
    depth: str | None
    model: str | None
    error: str | None
    version_saved: bool


@dataclass(frozen=True, slots=True)
class FindingCount:
    key: str
    rule: str
    severity: str
    versions: int
    occurrences: int


@dataclass(frozen=True, slots=True)
class ReceiptCounts:
    versions_with_receipts: int
    versions_without_receipts: int
    attempts: int
    completed: int
    empty: int
    unavailable: int
    other_unsuccessful: int
    versions_with_empty_or_unavailable: int


@dataclass(frozen=True, slots=True)
class UsageCounts:
    versions_with_usage: int
    versions_without_usage: int
    prompt_tokens: int
    completion_tokens: int
    prompt_tokens_per_version: int | None
    completion_tokens_per_version: int | None


@dataclass(frozen=True, slots=True)
class VersionGroup:
    key: str
    label: str
    versions: int
    ready: int
    needs_review: int
    failed: int
    findings: tuple[FindingCount, ...]
    receipts: ReceiptCounts
    usage: UsageCounts


@dataclass(frozen=True, slots=True)
class FailureCode:
    code: str
    jobs: int


@dataclass(frozen=True, slots=True)
class JobGroup:
    key: str
    label: str
    jobs: int
    queued: int
    running: int
    paused: int
    completed: int
    needs_review: int
    failed: int
    failed_without_version: int
    failed_with_version: int
    failure_codes: tuple[FailureCode, ...]


@dataclass(frozen=True, slots=True)
class VersionPopulation:
    bound: int
    in_window: int
    counted: int
    bound_reached: bool
    overall: VersionGroup
    by_template: tuple[VersionGroup, ...]
    by_depth: tuple[VersionGroup, ...]
    by_connection: tuple[VersionGroup, ...]


@dataclass(frozen=True, slots=True)
class JobPopulation:
    bound: int
    in_window: int
    counted: int
    bound_reached: bool
    overall: JobGroup
    by_template: tuple[JobGroup, ...]
    by_depth: tuple[JobGroup, ...]
    by_model: tuple[JobGroup, ...]


@dataclass(frozen=True, slots=True)
class CitationCheckOutcomes:
    """Human citation verdicts recorded in the window: counts and denominators only."""

    available: bool
    note: str
    bound: int = MAX_QUALITY_VERDICTS
    in_window: int = 0
    counted: int = 0
    bound_reached: bool = False
    current_verdicts: int = 0
    superseded_verdicts: int = 0
    citations_with_verdicts: int = 0
    supports: int = 0
    partly_supports: int = 0
    does_not_support: int = 0
    cannot_tell: int = 0


def _verdict_outcomes(total: int, rows: Sequence[CitationVerdict]) -> CitationCheckOutcomes:
    tally = tally_verdicts(rows)
    return CitationCheckOutcomes(
        True,
        CITATION_CHECKS_NOTE,
        MAX_QUALITY_VERDICTS,
        total,
        len(rows),
        total > len(rows),
        tally.current_verdicts,
        tally.superseded_verdicts,
        tally.citations_with_verdicts,
        tally.supports,
        tally.partly_supports,
        tally.does_not_support,
        tally.cannot_tell,
    )


@dataclass(frozen=True, slots=True)
class ResearchQualityScorecard:
    generated_at: datetime
    window_days: int
    since: datetime
    versions: VersionPopulation
    jobs: JobPopulation
    citation_checks: CitationCheckOutcomes


def _mean(total: int, count: int) -> int | None:
    return round(total / count) if count else None


def _findings(rows: Sequence[VersionOutcome]) -> tuple[FindingCount, ...]:
    occurrences: Counter[tuple[str, str]] = Counter()
    versions: Counter[tuple[str, str]] = Counter()
    for row in rows:
        occurrences.update(row.findings)
        versions.update(set(row.findings))
    ranked = sorted(versions, key=lambda key: (-versions[key], -occurrences[key], key))
    return tuple(
        FindingCount(f"{key[0]}:{key[1]}", key[0], key[1], versions[key], occurrences[key])
        for key in ranked[:TOP_FINDINGS]
    )


def _receipts(rows: Sequence[VersionOutcome]) -> ReceiptCounts:
    present = [row.receipts for row in rows if row.receipts is not None]
    statuses = Counter(status for receipts in present for status in receipts)
    return ReceiptCounts(
        versions_with_receipts=len(present),
        versions_without_receipts=len(rows) - len(present),
        attempts=sum(statuses.values()),
        completed=statuses["completed"],
        empty=statuses["empty"],
        unavailable=statuses["unavailable"],
        other_unsuccessful=sum(statuses[status] for status in UNSUCCESSFUL_RECEIPTS),
        versions_with_empty_or_unavailable=sum(
            1 for receipts in present if {"empty", "unavailable"} & set(receipts)
        ),
    )


def _usage(rows: Sequence[VersionOutcome]) -> UsageCounts:
    used = [
        row for row in rows if row.prompt_tokens is not None and row.completion_tokens is not None
    ]
    prompt = sum(row.prompt_tokens or 0 for row in used)
    completion = sum(row.completion_tokens or 0 for row in used)
    return UsageCounts(
        len(used),
        len(rows) - len(used),
        prompt,
        completion,
        _mean(prompt, len(used)),
        _mean(completion, len(used)),
    )


def _version_group(key: str, label: str, rows: Sequence[VersionOutcome]) -> VersionGroup:
    statuses = Counter(row.status for row in rows)
    return VersionGroup(
        key,
        label,
        len(rows),
        statuses["ready"],
        statuses["needs_review"],
        statuses["failed"],
        _findings(rows),
        _receipts(rows),
        _usage(rows),
    )


def _job_group(key: str, label: str, rows: Sequence[JobOutcome]) -> JobGroup:
    statuses = Counter(row.status for row in rows)
    failed = [row for row in rows if row.status == "failed"]
    codes = Counter(row.error for row in failed if row.error)
    ranked = sorted(codes.items(), key=lambda item: (-item[1], item[0]))[:TOP_FAILURE_CODES]
    return JobGroup(
        key=key,
        label=label,
        jobs=len(rows),
        queued=statuses["queued"],
        running=statuses["running"],
        paused=statuses["paused"],
        completed=statuses["completed"],
        needs_review=statuses["needs_review"],
        failed=len(failed),
        failed_without_version=sum(1 for row in failed if not row.version_saved),
        failed_with_version=sum(1 for row in failed if row.version_saved),
        failure_codes=tuple(FailureCode(code, count) for code, count in ranked),
    )


def _split[T, G](
    rows: Sequence[T],
    key: Callable[[T], str | None],
    labels: Mapping[str, str],
    build: Callable[[str, str, Sequence[T]], G],
) -> tuple[G, ...]:
    groups: dict[str, list[T]] = {}
    for row in rows:
        groups.setdefault(key(row) or NOT_RECORDED, []).append(row)
    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    return tuple(
        build(name, labels.get(name, "Not recorded" if name == NOT_RECORDED else name), members)
        for name, members in ordered
    )


def _label(value: str) -> str:
    return value if len(value) <= MAX_LABEL else f"{value[: MAX_LABEL - 3]}..."


def build_scorecard(
    *,
    generated_at: datetime,
    window_days: int,
    since: datetime,
    versions: tuple[int, Sequence[VersionOutcome]],
    jobs: tuple[int, Sequence[JobOutcome]],
    template_labels: Mapping[str, str],
    connection_labels: Mapping[str, str],
    verdicts: tuple[int, Sequence[CitationVerdict]] = (0, ()),
) -> ResearchQualityScorecard:
    version_total, version_rows = versions
    job_total, job_rows = jobs
    models = {row.model: _label(row.model) for row in job_rows if row.model}
    return ResearchQualityScorecard(
        generated_at=generated_at,
        window_days=window_days,
        since=since,
        versions=VersionPopulation(
            MAX_QUALITY_VERSIONS,
            version_total,
            len(version_rows),
            version_total > len(version_rows),
            _version_group("all", "All saved versions", version_rows),
            _split(version_rows, lambda row: row.template, template_labels, _version_group),
            _split(version_rows, lambda row: row.depth, {}, _version_group),
            _split(version_rows, lambda row: row.connection, connection_labels, _version_group),
        ),
        jobs=JobPopulation(
            MAX_QUALITY_JOBS,
            job_total,
            len(job_rows),
            job_total > len(job_rows),
            _job_group("all", "All report jobs", job_rows),
            _split(job_rows, lambda row: row.template, template_labels, _job_group),
            _split(job_rows, lambda row: row.depth, {}, _job_group),
            _split(job_rows, lambda row: row.model, models, _job_group),
        ),
        citation_checks=_verdict_outcomes(*verdicts),
    )


def known(value: object, choices: Iterable[str]) -> str | None:
    """A recorded dimension value, or None when absent or outside the known set."""
    return value if isinstance(value, str) and value in set(choices) else None
