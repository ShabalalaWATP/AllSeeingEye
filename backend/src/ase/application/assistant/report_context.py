"""Select small, exact-version report excerpts for Ask Eye without live collection."""

import re
from dataclasses import dataclass, replace
from uuid import UUID

from ase.application.assistant.sources import STOP_WORDS, safe_source_url
from ase.application.reports.access import GetReportUseCase
from ase.domain.assistant import (
    AssistantContext,
    AssistantInterpretation,
    AssistantQuestion,
    AssistantReportContext,
    AssistantSource,
)
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.evidence import injection_flags
from ase.domain.report_records import ReportVersion
from ase.domain.users import User

MAX_CANDIDATES = 300
MAX_SOURCES = 14
MAX_CHARS = 14_000
MAX_CLAIMS = 8
REPORT_WORDS = frozenset(
    {"report", "edition", "version", "say", "says", "said", "claim", "claims", "evidence"}
)


@dataclass(frozen=True, slots=True)
class _Candidate:
    source: AssistantSource
    labels: tuple[str, ...] = ()


def _terms(question: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            term
            for term in re.findall(r"[\w'-]{2,}", question.casefold())
            if term not in STOP_WORDS and term not in REPORT_WORDS
        )
    )[:16]


def _score(source: AssistantSource, terms: tuple[str, ...]) -> int:
    text = " ".join((source.title, source.summary, *source.details)).casefold()
    return sum(bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)) for term in terms)


def _claim(
    version_id: UUID,
    locator: str,
    title: str,
    text: str,
    labels: tuple[str, ...],
    detail: str = "",
) -> _Candidate | None:
    if not text.strip() or injection_flags(text, title):
        return None
    return _Candidate(
        AssistantSource(
            "",
            "report_claim",
            f"{version_id}:{locator}",
            f"report_version:{version_id}",
            title[:300],
            None,
            None,
            None,
            None,
            None,
            text[:1200],
            (
                f"Exact frozen report claim: {locator}.",
                f"{detail[:300]}" if detail else "",
                "Report evidence labels (not chat reference IDs): " + ", ".join(labels[:12])
                if labels
                else "No report evidence label is attached to this passage.",
            ),
        ),
        labels,
    )


def _claims(version: ReportVersion) -> list[_Candidate]:
    body = version.body
    rows: list[_Candidate | None] = []
    for index, judgement in enumerate(body.key_judgements[:20], 1):
        rows.append(
            _claim(
                version.id,
                f"key_judgement:{index}:{judgement.id}",
                f"Key judgement {judgement.id}",
                judgement.statement,
                (*judgement.supporting_evidence, *judgement.contradicting_evidence),
                f"Likelihood band: {judgement.probability.value}; "
                f"confidence: {judgement.confidence.value}.",
            )
        )
    for theme_index, theme in enumerate(body.reporting[:20], 1):
        for item_index, item in enumerate(theme.items[:20], 1):
            rows.append(
                _claim(
                    version.id,
                    f"reporting:{theme_index}:{item_index}",
                    f"Reporting: {theme.theme}",
                    item.text,
                    item.evidence,
                )
            )
    for index, section in enumerate(body.assessment[:20], 1):
        rows.append(
            _claim(
                version.id,
                f"assessment:{index}",
                f"Assessment: {section.heading}",
                section.text,
                section.evidence,
            )
        )
    for index, gap in enumerate(body.gaps[:20], 1):
        rows.append(
            _claim(
                version.id,
                f"gap:{index}",
                "Report information gap",
                gap.text,
                (),
                "This is a gap recorded in the report, not evidence that the event did not occur.",
            )
        )
    return [row for row in rows if row is not None]


def _evidence(version: ReportVersion) -> list[_Candidate]:
    rows: list[_Candidate] = []
    for item in version.evidence[:MAX_CANDIDATES]:
        if injection_flags(item.title, item.summary):
            continue
        rows.append(
            _Candidate(
                AssistantSource(
                    "",
                    "report_evidence",
                    f"{version.id}:evidence:{item.label}",
                    item.source_id,
                    item.title[:300],
                    safe_source_url(item.url),
                    item.published_at,
                    item.observed_at,
                    None,
                    item.grade,
                    (item.summary or "")[:600],
                    (
                        f"Frozen report evidence label: {item.label}.",
                        f"Declared source: {item.source_name[:160]}.",
                        "This is the saved title and summary, not a newly read original passage.",
                    ),
                    item.country_iso,
                    item.source_name[:160],
                ),
                (item.label,),
            )
        )
    return rows


def _choose(candidates: list[_Candidate], question: str) -> tuple[list[AssistantSource], int]:
    terms = _terms(question)
    scored = [(_score(row.source, terms), index, row) for index, row in enumerate(candidates)]
    matches = [row for row in scored if row[0] > 0] if terms else scored
    if not matches:
        return [], 0
    ranked = sorted(matches, key=lambda row: (-row[0], row[1]))
    chosen = [row[2] for row in ranked if row[2].source.kind == "report_claim"][:MAX_CLAIMS]
    evidence = [row[2] for row in ranked if row[2].source.kind == "report_evidence"]
    cited = {label for row in chosen for label in row.labels}
    linked = [
        row for row in candidates if row.source.kind == "report_evidence" and row.labels[0] in cited
    ]
    seen = {row.source.record_id for row in chosen}
    for row in (*linked, *evidence):
        if row.source.record_id not in seen:
            chosen.append(row)
            seen.add(row.source.record_id)
        if len(chosen) >= MAX_SOURCES:
            break
    result: list[AssistantSource] = []
    size = 0
    for row in chosen[:MAX_SOURCES]:
        source = row.source
        amount = len(source.title) + len(source.summary) + sum(map(len, source.details))
        if size + amount > MAX_CHARS:
            break
        size += amount
        result.append(replace(source, id=f"E{len(result) + 1}"))
    return result, len(matches)


class ReportContextReader:
    """Authorise the exact saved edition before retrieval and again before release."""

    def __init__(self, reports: GetReportUseCase) -> None:
        self.reports = reports

    async def collect(self, actor: User, question: AssistantQuestion) -> AssistantContext:
        if question.scope != "report" or question.report is None:
            raise InvalidRequest("Select an exact report version for report Q&A.")
        record, version = await self.reports.execute(
            actor, question.report.id, question.report.version
        )
        if version.report_id != record.id or version.number != question.report.version:
            raise Conflict("The selected report edition does not match its saved record.")
        anchor = AssistantReportContext(
            record.id,
            version.id,
            version.number,
            record.title[:300],
            version.data_cutoff,
        )
        candidates = [*_claims(version), *_evidence(version)][:MAX_CANDIDATES]
        selected, matched = _choose(candidates, question.question)
        return AssistantContext(
            tuple(selected),
            len(candidates),
            len({row.source_id for row in selected}),
            len(candidates) > len(selected) or len(version.evidence) > MAX_CANDIDATES,
            (
                "Only the selected immutable report edition and its frozen evidence were searched.",
                "Saved evidence titles and summaries are not newly retrieved original passages.",
                "This legacy edition has no exact frozen data cutoff."
                if version.data_cutoff is None
                else "The data cutoff is frozen in this edition.",
                "Search for newer evidence is a separate research action; "
                "this answer does not refresh the report.",
            ),
            matched_count=matched,
            clarification=(
                "The selected report edition has no matching claim or saved evidence excerpt. "
                "This does not establish absence; search for newer evidence separately."
                if not selected
                else None
            ),
            interpretation=AssistantInterpretation((), (), source_categories=("report",)),
            report=anchor,
        )

    async def require_current(self, actor: User, anchor: AssistantReportContext) -> None:
        record, version = await self.reports.execute(actor, anchor.id, anchor.version)
        if version.id != anchor.version_id or version.report_id != record.id:
            raise Conflict("The selected report edition changed during the answer.")
