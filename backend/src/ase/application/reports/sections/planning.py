"""Deterministic topics and immutable input identities for resumable report drafting."""

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ase.application.reports.templates import Template
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.llm import LlmProfile
from ase.domain.reports import KeyJudgement, ReportHeader

MAX_INITIAL_TOPICS = 6
MAX_TOPIC_LEAVES = 12
MAX_SPLIT_DEPTH = 2
MAX_EVIDENCE = 100
LEGACY_METHOD_VERSION = "report-sections-v1"
PREVIOUS_METHOD_VERSION = "report-sections-v2"
METHOD_VERSION = "report-sections-v3"
_LABEL = re.compile(r"E[1-9][0-9]{0,5}")
_STOP = frozenset(
    [
        "what",
        "which",
        "where",
        "when",
        "does",
        "have",
        "with",
        "from",
        "that",
        "this",
        "their",
        "there",
        "evidence",
        "reported",
        "supplied",
        "about",
    ]
)


@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    title: str
    evidence_labels: tuple[str, ...]
    eei_ids: tuple[str, ...] = ()
    parent: str | None = None
    depth: int = 0
    requirement_evidence: tuple[tuple[str, tuple[str, ...]], ...] = ()


def _terms(text: str) -> set[str]:
    return {word for word in re.findall(r"\w{3,}", text.casefold()) if word not in _STOP}


def _legacy_match(terms: set[str], eei_terms: Sequence[set[str]]) -> int | None:
    scores = [len(terms & row) for row in eei_terms]
    best = max(scores, default=0)
    return scores.index(best) if best else None


def _specific_match(
    terms: set[str],
    eei_terms: Sequence[set[str]],
    term_evidence_frequency: dict[str, int],
    evidence_count: int,
) -> int | None:
    """Match only discriminating terms, never a first-item tie on broad context."""
    requirement_frequency = {
        term: sum(term in row for row in eei_terms) for term in set().union(*eei_terms)
    }
    scores: list[int] = []
    for row in eei_terms:
        useful = {
            term
            for term in terms & row
            if requirement_frequency[term] == 1
            and (
                evidence_count < 3 or term_evidence_frequency.get(term, 0) * 5 < evidence_count * 3
            )
        }
        scores.append(len(useful))
    best = max(scores, default=0)
    winners = [index for index, score in enumerate(scores) if score == best and score > 0]
    return winners[0] if len(winners) == 1 else None


def plan_topics(
    evidence: Sequence[EvidenceItem],
    direction: Direction | None,
    *,
    method_version: str = METHOD_VERSION,
) -> tuple[Topic, ...]:
    labels = tuple(item.label for item in evidence)
    if (
        not 1 <= len(labels) <= MAX_EVIDENCE
        or len(set(labels)) != len(labels)
        or any(not _LABEL.fullmatch(label) for label in labels)
    ):
        raise ValueError("Section drafting requires bounded, uniquely labelled frozen evidence.")
    eeis = tuple(direction.eeis) if direction else ()
    eei_terms = tuple(_terms(text) for text in eeis)
    item_terms = {
        item.label: _terms(f"{item.title} {item.title_en or ''} {item.summary or ''}")
        for item in evidence
    }
    term_evidence_frequency = {
        term: sum(term in terms for terms in item_terms.values())
        for term in set().union(*item_terms.values())
    }
    assignments: dict[str, str] = {}
    groups: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for item in evidence:
        terms = item_terms[item.label]
        index = (
            _legacy_match(terms, eei_terms)
            if method_version == LEGACY_METHOD_VERSION
            else _specific_match(
                terms,
                eei_terms,
                term_evidence_frequency,
                len(evidence),
            )
        )
        key: tuple[str, tuple[str, ...]]
        if index is not None:
            requirement_id = f"EEI-{index + 1}"
            assignments[item.label] = requirement_id
            key = (f"{requirement_id}: {eeis[index]}"[:100], (requirement_id,))
        else:
            country = f" ({item.country_iso})" if item.country_iso else ""
            key = (f"{item.category.replace('_', ' ').capitalize()}{country}"[:100], ())
        groups.setdefault(key, []).append(item.label)
    if len(labels) <= 2:
        bindings = _bindings(labels, assignments) if method_version == METHOD_VERSION else ()
        return (
            Topic(
                "S1",
                "Supplied evidence",
                labels,
                tuple(requirement_id for requirement_id, _ in bindings),
                requirement_evidence=bindings,
            ),
        )
    parts = [
        (title, ids, tuple(items), _bindings(tuple(items), assignments))
        for (title, ids), items in groups.items()
    ]
    if len(parts) > MAX_INITIAL_TOPICS:
        retained, rest = parts[: MAX_INITIAL_TOPICS - 1], parts[MAX_INITIAL_TOPICS - 1 :]
        parts = [
            *retained,
            (
                "Further supplied evidence",
                tuple(dict.fromkeys(eei for _, ids, _, _ in rest for eei in ids)),
                tuple(label for _, _, items, _ in rest for label in items),
                tuple(binding for _, _, _, bindings in rest for binding in bindings),
            ),
        ]
    target = min(MAX_INITIAL_TOPICS, len(labels), max(4, math.ceil(len(labels) / 8)))
    while len(parts) < target:
        index = max(range(len(parts)), key=lambda at: len(parts[at][2]))
        title, ids, items, bindings = parts[index]
        if len(items) < 2:
            break
        middle = (len(items) + 1) // 2
        first, second = items[:middle], items[middle:]
        parts[index : index + 1] = [
            (title, ids, first, _filter_bindings(first, bindings)),
            (title, ids, second, _filter_bindings(second, bindings)),
        ]
    counts = {title: sum(row[0] == title for row in parts) for title, _, _, _ in parts}
    seen: dict[str, int] = {}
    topics = []
    for index, (title, ids, items, bindings) in enumerate(parts, 1):
        seen[title] = seen.get(title, 0) + 1
        name = f"{title} (part {seen[title]})" if counts[title] > 1 else title
        topics.append(
            Topic(
                f"S{index}",
                name,
                items,
                ids,
                requirement_evidence=bindings if method_version == METHOD_VERSION else (),
            )
        )
    return tuple(topics)


def _bindings(
    labels: Sequence[str], assignments: dict[str, str]
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    requirement_ids = dict.fromkeys(assignments[label] for label in labels if label in assignments)
    return tuple(
        (
            requirement_id,
            tuple(label for label in labels if assignments.get(label) == requirement_id),
        )
        for requirement_id in requirement_ids
    )


def _filter_bindings(
    labels: Sequence[str],
    bindings: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    allowed = frozenset(labels)
    return tuple(
        (requirement_id, selected)
        for requirement_id, evidence_labels in bindings
        if (selected := tuple(label for label in evidence_labels if label in allowed))
    )


def split_topic(topic: Topic) -> tuple[Topic, Topic] | None:
    if topic.depth >= MAX_SPLIT_DEPTH or len(topic.evidence_labels) < 2:
        return None
    middle = (len(topic.evidence_labels) + 1) // 2
    children = [
        Topic(
            f"{topic.id}.{index}",
            f"{topic.title[:105]} / {index}",
            labels,
            topic.eei_ids,
            topic.id,
            topic.depth + 1,
            _filter_bindings(labels, topic.requirement_evidence),
        )
        for index, labels in enumerate(
            (topic.evidence_labels[:middle], topic.evidence_labels[middle:]), 1
        )
    ]
    return children[0], children[1]


def canonical_json(value: Any) -> str:
    def convert(item: object) -> Any:
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, frozenset | set):
            return sorted(item)
        raise TypeError("Unsupported report packet value")

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        default=convert,
    )


def packet_digest(
    profile: LlmProfile,
    template: Template,
    header: ReportHeader,
    question: str | None,
    quality: QualityOfInformation,
    evidence: Sequence[EvidenceItem],
    previous: Sequence[KeyJudgement],
    direction: Direction | None,
    background: str | None,
    *,
    method_version: str = METHOD_VERSION,
) -> str:
    packet = canonical_json(
        {
            "method": method_version,
            "profile": profile.config_hash,
            "template": asdict(template),
            "header": asdict(header),
            "question": question,
            "quality": asdict(quality),
            "evidence": [asdict(item) for item in evidence],
            "previous": [asdict(row) for row in previous],
            "direction": asdict(direction) if direction else None,
            "background": background,
        }
    )
    if len(packet.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("The frozen report packet exceeds its size limit.")
    return hashlib.sha256(packet.encode("utf-8")).hexdigest()
