"""Historical actor references and conservative text-mention detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

MAX_ACTORS = 300
MAX_ASSOCIATED_NAMES = 24
MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 800
MAX_TECHNIQUES = 1_000
MAX_MENTION_TEXT = 20_000


@dataclass(frozen=True)
class CyberActorReference:
    group_id: str
    name: str
    associated_names: tuple[str, ...]
    description: str
    url: str
    modified_at: datetime
    technique_ids: tuple[str, ...]

    @property
    def technique_count(self) -> int:
        return len(self.technique_ids)


@dataclass(frozen=True)
class CyberActorCatalogue:
    source_id: str
    version: str
    released_at: datetime
    retrieved_at: datetime
    source_url: str
    source_sha256: str
    licence_url: str
    attribution: str
    limitations: str
    actors: tuple[CyberActorReference, ...]


@dataclass(frozen=True)
class CyberActorMention:
    """A name appears in supplied text; this never establishes responsibility."""

    group_id: str
    matched_name: str


@lru_cache(maxsize=2)
def _mention_patterns(
    actors: tuple[CyberActorReference, ...],
) -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    names: dict[str, set[str]] = {}
    references: dict[tuple[str, str], str] = {}
    for actor in actors[:MAX_ACTORS]:
        for name in (actor.name, *actor.associated_names[:MAX_ASSOCIATED_NAMES]):
            folded = name.casefold()
            # Short ordinary words are too ambiguous. Recognisable numbered actor
            # designators are useful even when short. Shared aliases are excluded.
            if len(name) > MAX_NAME_LENGTH or (
                sum(char.isalnum() for char in name) < 8
                and not re.fullmatch(r"(?:apt|fin|ta|unc)\d{1,5}", folded)
            ):
                continue
            names.setdefault(folded, set()).add(actor.group_id)
            references[(folded, actor.group_id)] = name
    return tuple(
        (
            group_id,
            references[(name, group_id)],
            re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)"),
        )
        for name, group_ids in sorted(names.items())
        if len(group_ids) == 1
        for group_id in group_ids
    )


def match_actor_mentions(
    text: str, actors: tuple[CyberActorReference, ...]
) -> tuple[CyberActorMention, ...]:
    """Return at most one explicit name mention per group in a bounded text prefix.

    This is deliberately incomplete: short/common and shared names are omitted,
    synonyms are not inferred, and negated mentions are still merely mentions.
    """
    folded = text[:MAX_MENTION_TEXT].casefold()
    matches: dict[str, CyberActorMention] = {}
    for group_id, name, pattern in _mention_patterns(actors[:MAX_ACTORS]):
        if group_id not in matches and pattern.search(folded):
            matches[group_id] = CyberActorMention(group_id, name)
    return tuple(matches[group_id] for group_id in sorted(matches))
