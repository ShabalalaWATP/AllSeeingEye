"""Conservative question constraints, with alternative topics and explicit text anchors."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ase.application.assistant.sources import query_terms, relevance
from ase.domain.assistant import AssistantSource, AssistantTimeRange
from ase.domain.country_subject_aliases import COUNTRY_SUBJECT_ALIASES
from ase.domain.country_subjects import source_text_country_matches
from ase.domain.errors import InvalidRequest
from ase.domain.events import Category

TOPICS = {
    "aviation": "aviation",
    "maritime": "maritime",
    "space": "space",
    "earthquake": "disaster",
    "fire": "disaster",
    "flood": "disaster",
    "tsunami": "disaster",
    "volcano": "disaster",
    "disaster": "disaster",
    "conflict": "conflict",
    "news": "news",
    "cyber": "cyber",
    "social": "social",
    "political": "political",
    "humanitarian": "humanitarian",
    "economic": "economic",
    "camera": "camera",
    "cable": "infrastructure",
    "nuclear": "infrastructure",
    "station": "infrastructure",
    "infrastructure": "infrastructure",
    "doctrine": "doctrine",
    "phia": "doctrine",
    "yardstick": "doctrine",
}
FILLER = frozenset(
    {
        "happened",
        "today",
        "yesterday",
        "week",
        "month",
        "year",
        "last",
        "those",
        "over",
        "under",
        "across",
        "report",
        "reports",
        "reported",
    }
)
# Output instructions are still sent to the model, but are not evidence entities.
# Only later, explicit presentation/claim clauses are removed. Substantive extra
# questions, including lowercase locations, remain mandatory retrieval constraints.
OUTPUT_INSTRUCTION = re.compile(
    r"^(?:please\s+)?(?:"
    r"(?:do not|don't|never|avoid)\s+(?:claim|assume|invent|fabricate|overstate|guess|"
    r"make assumptions)\b|"
    r"(?:keep|make)\s+(?:it|the answer|the response|your answer|your response)\b|"
    r"(?:format|structure)\s+(?:it|the answer|the response|your answer|your response)\b|"
    r"(?:respond|answer|write)\s+in\s+(?:(?:\d+|one|two|three|four|five)\s+)?"
    r"(?:plain|short|brief|concise|bullet|paragraph)\b|"
    r"(?:with|use)\s+(?:citations|references|bullet points|bullets|paragraphs)\b|"
    r"(?:give|provide|include)\s+(?:me\s+)?(?:\d+|one|two|three|four|five)\s+"
    r"(?:(?:short|brief|concise)\s+)?(?:observations|findings|limitations|sentences|"
    r"paragraphs|bullets|bullet points)\b)",
    re.IGNORECASE,
)
SCOPE_IN_FORMATTING = re.compile(
    r"\b(?:near|over|around|within|across|from|for|about|on|in)\s+"
    r"(?!(?:plain|short|brief|concise|bullet|paragraph|one|two|three|four|five)\b)"
    r"[^\W\d]",
    re.IGNORECASE,
)
EPISTEMIC_INSTRUCTION = re.compile(
    r"^(?:please\s+)?(?:do not|don't|never|avoid)\s+"
    r"(?:claim|assume|invent|fabricate|overstate|guess|make assumptions)\b",
    re.IGNORECASE,
)
UNSUPPORTED_EXCLUSION = re.compile(
    r"\b(?:exclude|excluding|except|without)\b|"
    r"\b(?:do not|don't)\s+(?:include|show|use)\b|\bnon[- ]military\b",
    re.IGNORECASE,
)
RELATIVE_WINDOW = re.compile(
    r"\b(?:last|past)\s+(\d{1,3})\s+(hours?|days?|weeks?)\b", re.IGNORECASE
)
NAMED_WINDOW = re.compile(r"\b(?:today|yesterday|last\s+(?:week|month|year))\b", re.IGNORECASE)
UNHANDLED_WINDOW = re.compile(
    r"\b(?:last|past|yesterday|today)\s+(?:\d+\s+)?(?:hours?|days?|weeks?|months?|years?)\b|"
    r"\b(?:since|between)\s+\w+",
    re.IGNORECASE,
)


PRESENTATION_WORDS = frozenset(
    {
        "answer",
        "response",
        "short",
        "brief",
        "concise",
        "plain",
        "text",
        "bullet",
        "bullets",
        "points",
        "paragraph",
        "paragraphs",
        "sentence",
        "sentences",
        "carefully",
        "citations",
        "references",
        "markdown",
        "words",
        "word",
        "length",
        "maximum",
        "max",
        "limit",
        "each",
        "cited",
    }
)


def _retrieval_text(text: str) -> tuple[str, bool]:
    clauses = re.split(
        r"(?<=[.!?;,])\s+|\n+|\s+(?=with (?:citations|references)\b)",
        text.strip(),
        flags=re.IGNORECASE,
    )
    retained = []
    unclear = False
    for clause in clauses:
        instruction = OUTPUT_INSTRUCTION.match(clause)
        if not instruction:
            retained.append(clause)
        elif not EPISTEMIC_INSTRUCTION.match(clause):
            # A presentation clause can add substantive scope, e.g. "Give two
            # observations in Japan". Keep that suffix, not the formatting words.
            scope = SCOPE_IN_FORMATTING.search(clause)
            if scope:
                retained.append(clause[scope.start() :])
            else:
                remainder = query_terms(clause[instruction.end() :], limit=None)
                # Unknown wording can encode a place/entity via any connective.
                # Never silently discard it and fall back to a wider search.
                unclear = unclear or any(term not in PRESENTATION_WORDS for term in remainder)
    return " ".join(retained), unclear


@dataclass(frozen=True, slots=True)
class QuestionIntent:
    terms: tuple[str, ...]
    topics: tuple[str, ...]
    countries: tuple[str, ...]
    anchors: tuple[str, ...]
    residual: tuple[str, ...]
    clarification: str | None = None
    time_range: AssistantTimeRange | None = None

    def accepts(self, category: str, source: AssistantSource) -> bool:
        relevant_topics = tuple(topic for topic in self.topics if TOPICS[topic] == category)
        if self.topics and (
            not relevant_topics or not any(relevance(source, (topic,)) for topic in relevant_topics)
        ):
            return False
        if self.countries:
            if source.country_iso is not None:
                if source.country_iso not in self.countries:
                    return False
            elif not source_text_country_matches(
                source.title,
                source.summary,
                self.countries,
                ignored_phrases=(source.publisher,) if source.publisher else (),
            ):
                return False
        if self.anchors and relevance(source, self.anchors) != len(self.anchors):
            return False
        if "military" in self.terms and not relevance(source, ("military",)):
            return False
        return bool(
            self.topics
            or self.countries
            or self.anchors
            or not self.residual
            or relevance(source, self.residual)
        )

    def event_query_military(self, category: Category) -> bool | None:
        return (
            True
            if "military" in self.terms
            and category
            in (
                Category.AVIATION,
                Category.MARITIME,
            )
            else None
        )


def _extract_time(text: str, now: datetime) -> tuple[str, AssistantTimeRange | None, bool]:
    """Resolve a small, explicit UTC/publication-time vocabulary; fail closed otherwise."""
    match = RELATIVE_WINDOW.search(text)
    named = NAMED_WINDOW.search(text)
    if (match and named) or (match and len(RELATIVE_WINDOW.findall(text)) > 1):
        return text, None, True
    if named and len(NAMED_WINDOW.findall(text)) > 1:
        return text, None, True
    if match:
        count = int(match.group(1))
        unit = match.group(2).casefold()
        hours = count * (1 if unit.startswith("hour") else 24 if unit.startswith("day") else 168)
        if not 1 <= hours <= 366 * 24:
            return text, None, True
        value = AssistantTimeRange(now - timedelta(hours=hours), now)
        text = text[: match.start()] + text[match.end() :]
    elif named:
        phrase = named.group().casefold().replace("  ", " ")
        if phrase in ("today", "yesterday"):
            local = now.astimezone(ZoneInfo("Europe/London"))
            midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
            if phrase == "yesterday":
                start, end = midnight - timedelta(days=1), midnight
            else:
                start, end = midnight, now
            value = AssistantTimeRange(start.astimezone(UTC), end.astimezone(UTC))
        else:
            days = {"last week": 7, "last month": 30, "last year": 365}[phrase]
            value = AssistantTimeRange(now - timedelta(days=days), now)
        text = text[: named.start()] + text[named.end() :]
    else:
        value = None
    return text, value, bool(UNHANDLED_WINDOW.search(text))


def interpret_question(text: str, *, now: datetime | None = None) -> QuestionIntent:
    now = now or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Question interpretation requires a timezone-aware clock.")
    text, unclear = _retrieval_text(text)
    text, time_range, ambiguous_time = _extract_time(text, now)
    terms = tuple(term for term in query_terms(text, limit=None) if term not in FILLER)
    if (
        unclear
        or ambiguous_time
        or not text
        or len(terms) > 24
        or UNSUPPORTED_EXCLUSION.search(text)
    ):
        return QuestionIntent(
            (),
            (),
            (),
            (),
            (),
            "Name the topics and places to include, or select a map item. "
            "This bounded search cannot reliably apply exclusions, ambiguous dates "
            "or very complex queries.",
        )
    topics = tuple(term for term in terms if term in TOPICS)
    country_words: set[str] = set()
    countries = []
    for code in COUNTRY_SUBJECT_ALIASES:
        matching = source_text_country_matches("", text, (code,))
        if matching:
            countries.append(code)
            country_words.update(word for match in matching for word in query_terms(match.text))
    if len(countries) > 8:
        raise InvalidRequest("Ask about at most eight named countries in one question.")
    residual = tuple(term for term in terms if term not in topics and term not in country_words)
    # Unrecognised meaningful terms may be locations or entities even in lowercase.
    # Require textual support; formatting/request words were removed separately.
    anchors = residual
    return QuestionIntent(terms, topics, tuple(countries), anchors, residual, time_range=time_range)
