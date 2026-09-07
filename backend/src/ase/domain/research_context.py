"""Immutable disclosures projected from saved evidence, without external identity resolution."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from ase.domain.event_similarity import COPY_SIMILARITY, jaccard, text_tokens
from ase.domain.events import JsonScalar
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import EvidenceAttribute, evidence_attributes_to_list

RESEARCH_CONTEXT_VERSION = "ase-research-context-v1"
MAX_CONTEXT_ITEMS = 200
CONTEXT_LIMITATIONS = (
    "This projection uses frozen evidence only; it performs no external verification.",
    "The timeline orders recorded publication timestamps, not verified event dates. "
    "Capture and observation stay separate; snapshot dates do not establish historical state.",
    "Identifiers and aliases are captured candidates, not confirmed matches to the subject. "
    "Names, tickers, registry handles and shared infrastructure never establish common ownership.",
    "Attribution edges are declarations in captured metadata, not authenticated source chains. "
    "A shared parent or possible copy is a caution, not proof of dependence or independence.",
    "Missing metadata stays unknown. Unlisted identities, attribution and relationships may exist.",
)


@dataclass(frozen=True, slots=True)
class ResearchTimelineEntry:
    evidence_label: str
    title: str
    published_at: datetime | None
    captured_at: datetime
    observed_at: datetime | None
    timestamp_basis: str | None
    date_precision: str | None
    current_snapshot: bool | None
    record_kind: str | None
    temporal_attributes: tuple[EvidenceAttribute, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapturedIdentityValue:
    namespace: str
    value: str


@dataclass(frozen=True, slots=True)
class ResearchIdentityCandidate:
    evidence_label: str
    identifiers: tuple[CapturedIdentityValue, ...]
    aliases: tuple[CapturedIdentityValue, ...]
    declared_match_status: str | None
    status: Literal["unverified_candidate"] = "unverified_candidate"


@dataclass(frozen=True, slots=True)
class ResearchSourceEdge:
    evidence_label: str
    collector_source_id: str
    relation: Literal["declared_publisher", "declared_account", "declared_source"]
    declared_name: str | None
    declared_id: str | None
    declared_url: str | None
    status: Literal["unverified_attribution"] = "unverified_attribution"


@dataclass(frozen=True, slots=True)
class ResearchSourceRelationship:
    evidence_labels: tuple[str, str]
    reasons: tuple[str, ...]
    shared_parent: str | None
    status: Literal["unverified_relationship"] = "unverified_relationship"


@dataclass(frozen=True, slots=True)
class ResearchContext:
    method_version: str
    timeline: tuple[ResearchTimelineEntry, ...]
    identity_candidates: tuple[ResearchIdentityCandidate, ...]
    source_chains: tuple[ResearchSourceEdge, ...]
    source_relationships: tuple[ResearchSourceRelationship, ...]
    limitations: tuple[str, ...]


SOURCE_RELATIONS: tuple[
    tuple[str, Literal["declared_publisher", "declared_account", "declared_source"]], ...
] = (
    ("original_publisher", "declared_publisher"),
    ("original_account", "declared_account"),
    ("original_source", "declared_source"),
)
IDENTIFIER_KEYS = ("cik", "accession", "domain", "registry_handle", "company_number", "lei")
ALIAS_KEYS = ("ticker", "name", "company_name", "alias", "aliases", "former_name")
TEMPORAL_KEYS = ("timestamp_basis", "date_precision", "current_snapshot", "record_kind")
SNAPSHOT_KINDS = frozenset(
    {
        "current_directory_snapshot",
        "current_dns_snapshot",
        "current_registry_snapshot",
        "current_certificate_snapshot",
    }
)


def _text(attributes: dict[str, JsonScalar], key: str) -> str | None:
    value = attributes.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _values(
    attributes: dict[str, JsonScalar], keys: tuple[str, ...]
) -> tuple[CapturedIdentityValue, ...]:
    # Preserve literal identifiers, including leading zeroes; never normalise into matches.
    return tuple(
        CapturedIdentityValue(key, value)
        for key in keys
        if (value := _text(attributes, key)) is not None
    )


def _timeline(item: EvidenceItem, attributes: dict[str, JsonScalar]) -> ResearchTimelineEntry:
    kind = _text(attributes, "record_kind")
    explicit = attributes.get("current_snapshot")
    snapshot = explicit if type(explicit) is bool else True if kind in SNAPSHOT_KINDS else None
    notes = []
    if item.observed_at is None:
        notes.append("Observation time was not captured.")
    if _text(attributes, "timestamp_basis") is None:
        notes.append("Publication timestamp basis was not captured.")
    if _text(attributes, "date_precision") is None:
        notes.append("Original date precision was not captured.")
    if snapshot:
        notes.append("Current snapshot only; its timestamp does not establish a historical event.")
    if explicit is False and kind in SNAPSHOT_KINDS:
        notes.append(
            "Captured snapshot flag conflicts with the declared current-snapshot record kind."
        )
    if any(
        date is not None and date.utcoffset() is None
        for date in (item.published_at, item.captured_at, item.observed_at)
    ):
        notes.append("A stored timestamp has no timezone; chronological placement is uncertain.")
    return ResearchTimelineEntry(
        item.label,
        item.title_en or item.title,
        item.published_at,
        item.captured_at,
        item.observed_at,
        _text(attributes, "timestamp_basis"),
        _text(attributes, "date_precision"),
        snapshot,
        kind,
        tuple(row for row in item.attributes if row.key in TEMPORAL_KEYS),
        tuple(notes),
    )


def _edges(item: EvidenceItem, attributes: dict[str, JsonScalar]) -> tuple[ResearchSourceEdge, ...]:
    rows: list[ResearchSourceEdge] = []
    for key, relation in SOURCE_RELATIONS:  # source fields are declarations only
        name = _text(attributes, key)
        identity = _text(attributes, key + "_id")
        url = _text(attributes, key + "_url")
        if name or identity or url:
            rows.append(
                ResearchSourceEdge(item.label, item.source_id, relation, name, identity, url)
            )
    return tuple(rows)


def _relationships(items: tuple[EvidenceItem, ...]) -> tuple[ResearchSourceRelationship, ...]:
    rows = []
    tokens = {item.label: text_tokens(item.title_en or item.title) for item in items}
    for index, item in enumerate(items):
        for other in items[:index]:
            reasons = []
            parent = None
            if item.independence_key.strip() and item.independence_key == other.independence_key:
                parent = item.independence_key
                reasons.append("shared_declared_parent")
            if item.content_hash and item.content_hash == other.content_hash:
                reasons.append("matching_content_hash")
            if jaccard(tokens[item.label], tokens[other.label]) >= COPY_SIMILARITY:
                reasons.append("similar_headline_possible_copy")
            if reasons:
                rows.append(
                    ResearchSourceRelationship((other.label, item.label), tuple(reasons), parent)
                )
    return tuple(rows)


def _chronology(item: EvidenceItem) -> tuple[bool, datetime, str]:
    naive = item.published_at is None or item.published_at.utcoffset() is None
    # Undated-zone legacy records sort last; UTC is only a comparison sentinel for those.
    stamp = (
        datetime.max.replace(tzinfo=UTC)
        if item.published_at is None or naive
        else item.published_at.astimezone(UTC)
    )
    return naive, stamp, item.label


def build_research_context(evidence: tuple[EvidenceItem, ...]) -> ResearchContext:
    if len(evidence) > MAX_CONTEXT_ITEMS:
        raise ValueError("Research context exceeds the evidence limit")
    labels = [item.label for item in evidence]
    if any(not label.strip() or len(label) > 64 for label in labels) or len(set(labels)) != len(
        labels
    ):
        raise ValueError("Research context needs bounded, nonblank, unique evidence labels")
    for item in evidence:
        evidence_attributes_to_list(item.attributes)
        if any(
            len(value) > 2000
            for value in (
                item.title,
                item.title_en or "",
                item.source_id,
                item.independence_key,
                item.content_hash,
            )
        ):
            raise ValueError("Research context has an oversized source or title field")
    items = tuple(sorted(evidence, key=lambda item: item.label))
    candidates: list[ResearchIdentityCandidate] = []
    edges: list[ResearchSourceEdge] = []
    timeline: list[ResearchTimelineEntry] = []
    for item in sorted(items, key=_chronology):
        attributes = {row.key: row.value for row in item.attributes}
        timeline.append(_timeline(item, attributes))
    for item in items:
        attributes = {row.key: row.value for row in item.attributes}
        identifiers, aliases = _values(attributes, IDENTIFIER_KEYS), _values(attributes, ALIAS_KEYS)
        if identifiers or aliases:
            candidates.append(
                ResearchIdentityCandidate(
                    item.label, identifiers, aliases, _text(attributes, "identity_match")
                )
            )
        edges.extend(_edges(item, attributes))
    return ResearchContext(
        RESEARCH_CONTEXT_VERSION,
        tuple(timeline),
        tuple(candidates),
        tuple(edges),
        _relationships(items),
        CONTEXT_LIMITATIONS,
    )
