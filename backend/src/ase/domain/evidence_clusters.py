"""Deterministic duplicate folding for syndicated, republished and translated copies.

Near-identical items are the same reporting reaching the pool several times, not
several independent observations. Folding them frees selection slots for distinct
reporting and makes the repetition visible. It is an explainable retrieval heuristic
using declared identifiers, normalised titles and publication proximity: it never
establishes independent corroboration, shared sourcing or plagiarism, and it never
calls a model.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from datetime import timedelta

from ase.domain.event_similarity import (
    COPY_SIMILARITY,
    MIN_SHARED_TOKENS,
    jaccard,
    title_tokens,
)
from ase.domain.events import Event
from ase.domain.similarity_candidates import token_candidate_pairs
from ase.domain.source_provenance import DisjointGroups

DUPLICATE_WINDOW = timedelta(hours=48)
MAX_CORROBORATION_MEMBERS = 24
_PUNCTUATION = re.compile(r"[^\w\s]+", re.UNICODE)
_TRACKING = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "cmpid", "igshid"})

CLUSTER_REASONS = {
    "identical_content_hash": "identical stored content hash",
    "same_link": "same canonical link",
    "same_title": "same normalised headline within 48 hours",
    "near_identical_text": "near-identical headline text within 48 hours",
}


def normalised_title(text: str | None) -> str:
    """Casefolded, punctuation-free headline text; never a claim-equivalence assertion."""
    if not text:
        return ""
    return " ".join(_PUNCTUATION.sub(" ", text.casefold()).split())


def canonical_link(url: str | None) -> str:
    """A comparable link identity: no scheme, no 'www.', no tracking query, no fragment."""
    if not url:
        return ""
    value = url.strip()
    for scheme in ("https://", "http://"):
        if value.lower().startswith(scheme):
            value = value[len(scheme) :]
            break
    value = value.split("#", 1)[0]
    address, _, query = value.partition("?")
    retained = [
        part
        for part in query.split("&")
        if part and not _tracking_parameter(part.split("=", 1)[0].casefold())
    ]
    address = address.rstrip("/")
    if address.lower().startswith("www."):
        address = address[4:]
    host, _, path = address.partition("/")
    address = f"{host.casefold()}/{path}" if path else host.casefold()
    return f"{address}?{'&'.join(sorted(retained))}" if retained else address


def _tracking_parameter(name: str) -> bool:
    return name.startswith("utm_") or name in _TRACKING


def _titles(event: Event) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            value
            for value in (normalised_title(event.title), normalised_title(event.title_en))
            if len(value) >= 8
        )
    )


def _close(left: Event, right: Event) -> bool:
    if left.published_at is None or right.published_at is None:
        return False
    return abs(left.published_at - right.published_at) <= DUPLICATE_WINDOW


def _exact_pairs(events: Sequence[Event]) -> list[tuple[str, str, str]]:
    """Declared identity links, which do not need publication proximity."""
    identities: tuple[tuple[Callable[[Event], str], str], ...] = (
        (lambda event: event.content_hash, "identical_content_hash"),
        (lambda event: canonical_link(event.url), "same_link"),
    )
    pairs: list[tuple[str, str, str]] = []
    for identity, reason in identities:
        seen: dict[str, str] = {}
        for event in events:
            key = identity(event)
            if not key:
                continue
            first = seen.setdefault(key, event.id)
            if first != event.id:
                pairs.append((first, event.id, reason))
    return pairs


def _title_pairs(events: Sequence[Event]) -> list[tuple[str, str, str]]:
    """Republished or translated copies of one headline inside the proximity window."""
    pairs: list[tuple[str, str, str]] = []
    by_title: dict[str, list[Event]] = {}
    for event in events:
        for title in _titles(event):
            by_title.setdefault(title, []).append(event)
    for group in by_title.values():
        for other in group[1:]:
            if group[0].category is other.category and _close(group[0], other):
                pairs.append((group[0].id, other.id, "same_title"))
    return pairs


def _near_pairs(events: Sequence[Event]) -> list[tuple[str, str, str]]:
    """Bounded near-duplicate joins at the copy threshold, never the story threshold."""
    ordered = sorted(events, key=lambda event: event.id)
    words = [title_tokens(event) for event in ordered]
    pairs: list[tuple[str, str, str]] = []
    for left, right in token_candidate_pairs(words):
        first, second = ordered[left], ordered[right]
        if first.category is not second.category or not _close(first, second):
            continue
        if len(words[left] & words[right]) < MIN_SHARED_TOKENS:
            continue
        if jaccard(words[left], words[right]) >= COPY_SIMILARITY:
            pairs.append((first.id, second.id, "near_identical_text"))
    return pairs


ClusterKeys = dict[str, str]
ClusterReasons = dict[str, tuple[str, ...]]


def duplicate_clusters(events: Sequence[Event]) -> tuple[ClusterKeys, ClusterReasons]:
    """Fold near-identical items; return each event's cluster key and that key's reasons.

    Order-independent: the cluster key is the smallest member identifier. Distinct
    reporting that merely shares a topic stays separate, because the thresholds are
    the copy thresholds, not the story thresholds.
    """
    groups = DisjointGroups(event.id for event in events)
    reasons: dict[str, set[str]] = {}
    for first, second, reason in (
        *_exact_pairs(events),
        *_title_pairs(events),
        *_near_pairs(events),
    ):
        groups.union(first, second)
        reasons.setdefault(groups.find(first), set()).add(reason)
    keys: dict[str, str] = {}
    smallest: dict[str, str] = {}
    folded: dict[str, set[str]] = {}
    for event in events:
        root = groups.find(event.id)
        current = smallest.get(root)
        smallest[root] = event.id if current is None or event.id < current else current
    for root, found in reasons.items():
        folded.setdefault(smallest[groups.find(root)], set()).update(found)
    for event in events:
        keys[event.id] = smallest[groups.find(event.id)]
    return keys, {key: tuple(sorted(found)) for key, found in folded.items()}


def cluster_reason_text(reasons: Sequence[str]) -> str:
    return "; ".join(CLUSTER_REASONS.get(reason, reason) for reason in reasons)
