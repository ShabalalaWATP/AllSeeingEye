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
    # Wording from the reference profile ("attributed to", "state-sponsored"), never
    # this application's own judgement. None means the profile states no such link.
    state_association: str | None = None

    @property
    def technique_count(self) -> int:
        return len(self.technique_ids)


_STATES: tuple[tuple[str, str, str], ...] = (
    # (label, nationality terms, named organs) all matched case-insensitively.
    ("Russia", r"russia|russian", r"gru|fsb|svr|main intelligence directorate|federal security"),
    (
        "China",
        r"people['’]s republic of china|china|chinese|prc",  # noqa: RUF001
        r"ministry of state security|people['’]s liberation army",  # noqa: RUF001
    ),
    ("Iran", r"iran|iranian", r"irgc|islamic revolutionary guard|ministry of intelligence"),
    ("North Korea", r"north korea|north korean|dprk", r"reconnaissance general bureau"),
    ("Pakistan", r"pakistan|pakistani", r"(?!x)x"),
    ("India", r"india|indian", r"(?!x)x"),
    ("Vietnam", r"vietnam|vietnamese", r"(?!x)x"),
    ("Belarus", r"belarus|belarusian", r"(?!x)x"),
    ("Syria", r"syria|syrian", r"(?!x)x"),
    ("Lebanon", r"lebanon|lebanese", r"(?!x)x"),
    ("South Korea", r"south korea|south korean", r"(?!x)x"),
    ("Israel", r"israel|israeli", r"(?!x)x"),
    ("Turkey", r"turkey|turkish|türkiye", r"(?!x)x"),
    ("United Arab Emirates", r"united arab emirates|uae|emirati", r"(?!x)x"),
)
_ATTRIBUTION_CUE = (
    r"(?:attributed to|sponsored by|on behalf of|operated by|run by|working for|"
    r"affiliated with|linked to|associated with|tied to|connected to|aligned with|"
    r"assessed to be|believed to be|suspected to be|likely|part of|element within|"
    r"subordinate to|controlled by|directed by|operat(?:e|es|ed|ing) (?:out of|from))"
)
_ADJECTIVE_NOUN = (
    r"\)?(?:\s*\([A-Za-z]{2,5}\))?[- '’–—]*"  # noqa: RUF001
    r"(?:state|government|based|sponsored|backed|linked|aligned|affiliated|nexus|origins?|"
    r"intelligence|military|cyber|espionage|threat|hackers|actors?|group|apt|"
    r"ministry|general staff|main|federal|foreign|people|security|reconnaissance|"
    r"islamic|army|s ministry|s general|s main|s federal|s foreign|s people|s intelligence|"
    r"s military|s state|s government|s cyber|s reconnaissance|s islamic|s security)"
)
_TARGETING_CUE = re.compile(
    r"\b(?:target(?:s|ed|ing)?|against|victims?|focus(?:ed|ing|es)?|including|emphasis|"
    r"interest in|operations|campaigns? in|primarily in|located in|entities in|"
    r"organi[sz]ations? in|based mostly in)\b",
    re.IGNORECASE,
)


_HEDGE = re.compile(
    r"circumstantial|could be|may be|might be|possibl[ey]|unconfirmed|reportedly|allegedly|"
    r"speculat|some researchers|compared (?:to|with)|similar(?:ities)? to|resembl|"
    r"no (?:formal |confirmed |established )?(?:attribution|link)|not (?:been )?confirmed|"
    r"not been (?:definitively |formally )?attributed",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _state_patterns() -> tuple[re.Pattern[str], tuple[tuple[str, re.Pattern[str]], ...]]:
    any_term = "|".join(terms for _, terms, _ in _STATES)
    cue = re.compile(_ATTRIBUTION_CUE + r"[^.;]{0,80}?\b(" + any_term + r")\b", re.IGNORECASE)
    rows = tuple(
        (
            label,
            re.compile(
                r"\b(?:" + terms + r")" + _ADJECTIVE_NOUN + r"\b|\b(?:" + organs + r")\b",
                re.IGNORECASE,
            ),
        )
        for label, terms, organs in _STATES
    )
    return cue, rows


def _label_for(term: str) -> str | None:
    folded = term.casefold()
    for label, terms, _ in _STATES:
        if re.fullmatch(terms, folded):
            return label
    return None


def assessed_state_association(description: str) -> str | None:
    """The state a reference profile itself associates a group with, or None.

    Only sentences carrying an explicit attribution cue, a nationality-plus-role
    phrase or a named state organ count. Hedged sentences and phrases that merely
    describe targets are ignored. This is bounded extraction of the source's
    wording, not this application's own analysis.
    """
    cue, rows = _state_patterns()
    for sentence in re.split(r"(?<=[.;])\s+", description[:MAX_DESCRIPTION_LENGTH]):
        if _HEDGE.search(sentence):
            continue
        cued = cue.search(sentence)
        if cued and (label := _label_for(cued.group(1))):
            return label
        earliest: tuple[int, str] | None = None
        for label, pattern in rows:
            match = pattern.search(sentence)
            if (
                match
                and not _TARGETING_CUE.search(sentence[: match.start()])
                and (earliest is None or match.start() < earliest[0])
            ):
                earliest = (match.start(), label)
        if earliest:
            return earliest[1]
    return None


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
