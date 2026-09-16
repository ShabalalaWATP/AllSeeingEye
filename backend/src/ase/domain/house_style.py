"""House-style rules for model-authored prose: UK spelling, punctuation and plain text.

Mechanical and advisory only. A violation is named, with the expected form, so an
analyst can correct it. Nothing here edits the report: silently rewriting a model's
words would change what the report says without anyone seeing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_STYLE_REPORTS = 10

# Only unambiguous pairs. Words whose American form is also correct British English in
# some sense (program, meter, practice, license, percent) are deliberately absent.
UK_SPELLINGS: dict[str, str] = {
    "organize": "organise",
    "organized": "organised",
    "organizing": "organising",
    "organization": "organisation",
    "organizations": "organisations",
    "recognize": "recognise",
    "recognized": "recognised",
    "analyze": "analyse",
    "analyzed": "analysed",
    "analyzing": "analysing",
    "emphasize": "emphasise",
    "emphasized": "emphasised",
    "prioritize": "prioritise",
    "prioritized": "prioritised",
    "mobilize": "mobilise",
    "mobilized": "mobilised",
    "mobilization": "mobilisation",
    "stabilize": "stabilise",
    "stabilized": "stabilised",
    "destabilize": "destabilise",
    "destabilizing": "destabilising",
    "normalize": "normalise",
    "utilize": "utilise",
    "realize": "realise",
    "minimize": "minimise",
    "maximize": "maximise",
    "criticize": "criticise",
    "characterize": "characterise",
    "characterized": "characterised",
    "summarize": "summarise",
    "defense": "defence",
    "defenses": "defences",
    "offense": "offence",
    "color": "colour",
    "behavior": "behaviour",
    "behaviors": "behaviours",
    "center": "centre",
    "centers": "centres",
    "centered": "centred",
    "labor": "labour",
    "honor": "honour",
    "favor": "favour",
    "neighbor": "neighbour",
    "neighbors": "neighbours",
    "harbor": "harbour",
    "armor": "armour",
    "armored": "armoured",
    "rumor": "rumour",
    "rumors": "rumours",
    "humor": "humour",
    "traveled": "travelled",
    "traveling": "travelling",
    "canceled": "cancelled",
    "canceling": "cancelling",
    "modeling": "modelling",
    "labeled": "labelled",
    "fueled": "fuelled",
    "signaling": "signalling",
    "totaled": "totalled",
    "fulfill": "fulfil",
    "maneuver": "manoeuvre",
    "maneuvers": "manoeuvres",
    "catalog": "catalogue",
    "dialog": "dialogue",
    "judgment": "judgement",
    "judgments": "judgements",
    "airplane": "aeroplane",
    "gray": "grey",
    "kilometers": "kilometres",
    "liters": "litres",
}

_SPELLING = re.compile(
    r"\b(" + "|".join(sorted(UK_SPELLINGS, key=len, reverse=True)) + r")\b", re.IGNORECASE
)
_EM_DASH = re.compile("\\u2014|\\s\\u2013\\s")
_MARKUP = (
    (re.compile(r"<\s*/?\s*[A-Za-z][A-Za-z0-9-]*\s*/?\s*>"), "an HTML tag"),
    (re.compile(r"&(?:nbsp|amp|lt|gt|quot|#\d{2,5});"), "an HTML entity"),
    (re.compile(r"\*\*|__(?=\w)"), "Markdown emphasis"),
    (re.compile(r"(?m)^\s{0,3}#{1,6}\s"), "a Markdown heading"),
    (re.compile(r"(?m)^\s{0,3}[-*+]\s+\S"), "a Markdown bullet"),
    (re.compile(r"`"), "a Markdown code marker"),
    (re.compile(r"\[[^\]\n]{1,80}\]\([^)\n]{1,200}\)"), "a Markdown link"),
)
# Evidence labels belong in the structured citation lists, not in the sentence.
_INLINE_CITATION = re.compile(r"[\[(]\s*E\d{1,3}(?:\s*,\s*E\d{1,3})*\s*[\])]")


@dataclass(frozen=True, slots=True)
class StyleViolation:
    kind: str
    found: str
    expected: str
    explanation: str


def _spelling_violations(text: str) -> list[StyleViolation]:
    found: list[StyleViolation] = []
    for match in _SPELLING.finditer(text):
        word = match.group(0)
        expected = UK_SPELLINGS[word.casefold()]
        found.append(
            StyleViolation(
                "spelling",
                word,
                expected,
                f"“{word}” is American spelling; the house style is “{expected}”.",
            )
        )
    return found


def style_violations(text: str) -> tuple[StyleViolation, ...]:
    """Every house-style problem in one passage, in a fixed order per passage."""
    found = _spelling_violations(text)
    if _EM_DASH.search(text):
        found.append(
            StyleViolation(
                "punctuation",
                "—",
                ", or a shorter sentence",
                "The prose uses a dash where the house style uses a comma, a colon, "
                "brackets or a shorter sentence.",
            )
        )
    for pattern, description in _MARKUP:
        match = pattern.search(text)
        if match is not None:
            found.append(
                StyleViolation(
                    "markup",
                    match.group(0).strip(),
                    "plain text",
                    f"A structured field contains {description}; these fields are "
                    "rendered as plain text, so the markup is shown to the reader.",
                )
            )
    citation = _INLINE_CITATION.search(text)
    if citation is not None:
        found.append(
            StyleViolation(
                "citation_format",
                citation.group(0),
                "the field's evidence list",
                f"The sentence writes the citation {citation.group(0)} inline; citations "
                "belong in the field's evidence list so they can be checked.",
            )
        )
    return tuple(found)
