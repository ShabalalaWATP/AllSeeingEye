"""Conservative grouping of declared provenance, without asserting source independence."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from ase.domain.event_similarity import COPY_SIMILARITY, jaccard, text_tokens
from ase.domain.source_ratings import SourceRating, unassessed_source_rating


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """Registry metadata; an organisation key does not prove independent reporting."""

    source_id: str
    independence_key: str
    name: str
    instrument: bool = False
    flags: frozenset[str] = frozenset()
    rating: SourceRating = field(default_factory=unassessed_source_rating)


class DisjointGroups:
    """Transitive equivalence groups for topic and provenance links."""

    def __init__(self, ids: Iterable[str]) -> None:
        self._parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(a)] = self.find(b)


@dataclass(frozen=True, slots=True)
class ProvenanceItem:
    id: str
    organisation: str | None
    title: str
    content_hash: str = ""


@dataclass(frozen=True, slots=True)
class OrganisationGroups:
    group_of: dict[str, str]
    known_groups: frozenset[str]
    possible_copies: bool


def organisation_groups(items: Sequence[ProvenanceItem]) -> OrganisationGroups:
    """Fold declared parents and possible copies transitively, independent of input order.

    Similar headlines may reflect common facts rather than copying. Folding them is a
    conservative counting guard, not a finding of plagiarism or shared sourcing. Unknown
    provenance never establishes an additional known organisation. Empty hashes do not
    match; callers must pass hashes of content, not arbitrary default values.
    """
    groups = DisjointGroups(item.id for item in items)
    by_organisation: dict[str | None, str] = {}
    tokens = {item.id: text_tokens(item.title) for item in items}
    possible_copies = False
    for index, item in enumerate(items):
        organisation = item.organisation or None
        if organisation in by_organisation:
            groups.union(item.id, by_organisation[organisation])
        else:
            by_organisation[organisation] = item.id
        for other in items[:index]:
            same_content = bool(item.content_hash) and item.content_hash == other.content_hash
            if same_content or jaccard(tokens[item.id], tokens[other.id]) >= COPY_SIMILARITY:
                groups.union(item.id, other.id)
                possible_copies = possible_copies or organisation != (other.organisation or None)
    group_of = {item.id: groups.find(item.id) for item in items}
    return OrganisationGroups(
        group_of=group_of,
        known_groups=frozenset(group_of[item.id] for item in items if item.organisation),
        possible_copies=possible_copies,
    )
