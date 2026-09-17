"""Conservative lexical eligibility for an explicit subject in a named locality.

This is not a geocoder or a relevance classifier. Only a short terminal locality
clause with proper-name casing is recognised. Ambiguous wording keeps the existing
general selection. Recognised requests require source text for both constraints;
country/category metadata and generated search phrases cannot supply that proof.
"""

import re
from dataclasses import dataclass

from ase.application.assistant.sources import query_terms
from ase.domain.country_subject_aliases import COUNTRY_SUBJECT_ALIASES
from ase.domain.events import Event
from ase.domain.languages import LANGUAGES
from ase.domain.research_scope import COUNTRY_CODES

_LOCALITY = re.compile(r"\b(?:in|near|around)\s+", re.IGNORECASE)
_NAME = re.compile(r"[^\W\d_]+(?:[-'\u2019][^\W\d_]+)*", re.UNICODE)
_CONNECTIVES = frozenset({"of", "the", "de", "del", "la", "du"})
_AMBIGUOUS = frozenset(
    [
        "last",
        "past",
        "next",
        "present",
        "future",
        "relation",
        "respect",
        "response",
        "terms",
        "addition",
        "particular",
        "general",
        "detail",
        "time",
        "hour",
        "hours",
        "day",
        "days",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "today",
        "yesterday",
        "tomorrow",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "recent",
        "current",
        "north",
        "south",
        "east",
        "west",
        "northern",
        "southern",
        "eastern",
        "western",
    ]
)
_REQUEST_WORDS = frozenset(
    [
        "need",
        "want",
        "update",
        "updates",
        "briefing",
        "briefings",
        "general",
        "news",
        "headline",
        "headlines",
        "story",
        "stories",
        "report",
        "reports",
        "reported",
        "happened",
        "today",
        "yesterday",
        "week",
        "month",
        "year",
        "last",
        "over",
        "under",
        "across",
        "those",
        "known",
        "know",
        "assess",
        "assessment",
        "assessments",
        "analyse",
        "analysis",
        "review",
        "research",
        "intelligence",
        "developments",
        "changed",
    ]
)
_COUNTRY_NAMES = frozenset(
    name.casefold() for names in COUNTRY_SUBJECT_ALIASES.values() for name in names
)
# These only suppress a locality inference. They never annotate evidence with a
# country, so ambiguous shorthand stays separate from reviewed country subjects.
_COUNTRY_SPELLINGS = frozenset(code.casefold() for code in COUNTRY_CODES) | {
    "uk",
    "usa",
    "britain",
    "america",
    "georgia",
    "guinea",
    "jordan",
    "congo",
    "korea",
}
_LANGUAGE_NAMES = frozenset(
    name.casefold()
    for language in LANGUAGES
    for name in (
        re.split(r"[(,]", language.label, maxsplit=1)[0].strip(),
        language.native_label,
        language.code,
    )
)
# Modest wording alternatives, not inferred causality: a fire alone is not an attack.
_SUBJECT_ALIASES = {"strike": "attack", "bombing": "attack", "bombardment": "attack"}


def _subject_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return _SUBJECT_ALIASES.get(token, token)


def _words(text: str) -> tuple[str, ...]:
    return tuple(
        word.casefold().removesuffix("'s").removesuffix("\u2019s") for word in _NAME.findall(text)
    )


def _contains_locality(text: str, locality: tuple[str, ...]) -> bool:
    words = _words(text)
    return any(
        words[index : index + len(locality)] == locality
        for index in range(len(words) - len(locality) + 1)
    )


@dataclass(frozen=True, slots=True)
class TargetedEvidenceScope:
    locality: tuple[str, ...]
    subjects: frozenset[str]

    def accepts(self, event: Event) -> bool:
        """Allow denials and consequences across categories when source text connects them."""
        fields = tuple(value for value in (event.title, event.title_en, event.summary) if value)
        return any(_contains_locality(value, self.locality) for value in fields) and bool(
            self.subjects.intersection(
                _subject_token(term) for term in query_terms(" ".join(fields), limit=None)
            )
        )


def targeted_evidence_scope(question: str | None) -> TargetedEvidenceScope | None:
    """Recognise bounded 'subject in Place' requests, without trusting model rewrites.

    Lowercase/complex place descriptions, country-wide requests and temporal or
    explanatory suffixes remain general. No place aliases are guessed, so alternate
    spellings need textual support in an original or translated source field.
    """
    if not question:
        return None
    matches = tuple(_LOCALITY.finditer(question))
    if not matches:
        return None
    match = matches[-1]
    place = question[match.end() :].strip().rstrip(".!?").strip()
    words = _NAME.findall(place)
    if (
        not 1 <= len(words) <= 4
        or " ".join(words) != place
        or place.casefold() in _COUNTRY_NAMES
        or place.casefold() in _COUNTRY_SPELLINGS
        or re.fullmatch(r"[A-Z]{2,3}", place) is not None
        or any(
            place.casefold() == name or place.casefold().endswith(f" {name}")
            for name in _LANGUAGE_NAMES
        )
        or _AMBIGUOUS.intersection(word.casefold() for word in words)
        or any(
            not word[0].isupper() and not (index and word.casefold() in _CONNECTIVES)
            for index, word in enumerate(words)
        )
    ):
        return None
    subjects = frozenset(
        _subject_token(term)
        for term in query_terms(question[: match.start()], limit=None)
        if term not in _REQUEST_WORDS
    )
    if not 1 <= len(subjects) <= 12:
        return None
    return TargetedEvidenceScope(_words(place), subjects)
