"""Bounded keyword lenses over war reporting. A lens is a text match, never a judgement."""

from __future__ import annotations

import re
from enum import StrEnum

MAX_LENS_TEXT = 3_000


class Lens(StrEnum):
    EQUIPMENT = "equipment"
    WORKFORCE = "workforce"
    CASUALTIES = "casualties"
    STRIKES = "strikes"
    DIPLOMACY = "diplomacy"


def _words(*terms: str) -> re.Pattern[str]:
    return re.compile(r"(?<![\w-])(?:" + "|".join(terms) + r")(?![\w-])", re.IGNORECASE)


_EQUIPMENT = _words(
    r"tanks?",
    r"armou?red (?:vehicles?|personnel carriers?)",
    r"IFVs?",
    r"APCs?",
    r"artillery",
    r"howitzers?",
    r"HIMARS",
    r"ATACMS",
    r"Patriot(?: (?:systems?|batter(?:y|ies)|missiles?|interceptors?))?",
    r"air[- ]defen[cs]e",
    r"missile (?:systems?|launchers?|batter(?:y|ies))",
    r"F-16s?",
    r"Mirage(?: 2000)?",
    r"Gripens?",
    r"drones?",
    r"UAVs?",
    r"FPVs?",
    r"Shaheds?",
    r"Gerans?",
    r"Iskanders?",
    r"Kinzhals?",
    r"Oreshnik",
    r"glide bombs?",
    r"Leopards?(?: 2)?",
    r"Abrams",
    r"Bradleys?",
    r"Storm Shadow",
    r"SCALP",
    r"Taurus",
    r"Neptune",
    r"Flamingo",
    r"ammunition",
    r"shells",
    r"weapons? (?:packages?|deliver(?:y|ies)|shipments?)",
    r"military aid",
    r"electronic warfare",
    r"jamming",
    r"Starlink",
    r"interceptor drones?",
    r"fibre[- ]optic",
    r"Lancets?",
)
_WORKFORCE = _words(
    r"mobili[sz]ation",
    r"mobili[sz]ed",
    r"conscription",
    r"conscripts?",
    r"recruit(?:s|ment|ing|ed)?",
    r"draft(?:ees?| offices?| evasion)?",
    r"enlist(?:ment|ed|ing)?",
    r"contract (?:soldiers?|service|servicemen)",
    r"demobili[sz]ation",
    r"reservists?",
    r"manpower",
    r"personnel shortages?",
    r"rotation",
    r"foreign fighters?",
    r"mercenar(?:y|ies)",
    r"North Korean (?:troops|soldiers|forces)",
    r"DPRK (?:troops|soldiers|forces)",
    r"desert(?:ers?|ion)",
    r"AWOL",
    r"Storm[- ]Z",
    r"Wagner",
    r"Africa Corps",
    r"volunteers?",
    r"territorial (?:defen[cs]e|recruitment)",
)
_CASUALTIES = _words(
    r"killed",
    r"dead",
    r"deaths?",
    r"died",
    r"wounded",
    r"injured",
    r"casualt(?:y|ies)",
    r"fatalit(?:y|ies)",
    r"bodies",
    r"prisoners? of war",
    r"POWs?",
    r"missing in action",
    r"death toll",
    r"civilian(?:s)? (?:killed|injured|harm)",
    r"personnel losses",
    r"irrecoverable losses",
    r"repatriat(?:ed|ion)",
)
_STRIKES = _words(
    r"(?:missile|drone|air|artillery|rocket|glide[- ]bomb|ballistic) (?:strikes?|attacks?)",
    r"strikes?",
    r"struck",
    r"shell(?:ed|ing)",
    r"explosions?",
    r"air raid",
    r"shot down",
    r"intercepted",
    r"blackouts?",
    r"energy infrastructure",
    r"refiner(?:y|ies)",
    r"oil depots?",
    r"airfields?",
    r"long[- ]range",
)
_DIPLOMACY = _words(
    r"ceasefire",
    r"truce",
    r"peace (?:plan|talks|deal|agreement|process|proposal)",
    r"negotiat(?:ions?|e|ed|ing|ors?)",
    r"sanctions?",
    r"summit",
    r"envoys?",
    r"diplomatic",
    r"ambassadors?",
    r"security guarantees?",
    r"NATO",
    r"accession",
    r"memorandum",
    r"prisoner (?:exchange|swap)",
    r"peacekeep(?:ers|ing)",
    r"coalition of the willing",
)
_PATTERNS: tuple[tuple[Lens, re.Pattern[str]], ...] = (
    (Lens.EQUIPMENT, _EQUIPMENT),
    (Lens.WORKFORCE, _WORKFORCE),
    (Lens.CASUALTIES, _CASUALTIES),
    (Lens.STRIKES, _STRIKES),
    (Lens.DIPLOMACY, _DIPLOMACY),
)


def lenses_for(text: str) -> frozenset[Lens]:
    """Every lens whose vocabulary appears in the bounded text."""
    sample = text[:MAX_LENS_TEXT]
    return frozenset(lens for lens, pattern in _PATTERNS if pattern.search(sample))
