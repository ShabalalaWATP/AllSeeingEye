"""Which retained items belong on the Ukraine page, and in which reporting group."""

from __future__ import annotations

import re
from enum import StrEnum

from ase.domain.events import Event

MAX_RELEVANCE_TEXT = 2_000


class UpdateGroup(StrEnum):
    ASSESSMENTS = "assessments"
    UKRAINIAN = "ukrainian"
    RUSSIAN = "russian"
    INTERNATIONAL = "international"


ASSESSMENT_SOURCES = frozenset(
    {"isw_assessments", "gov_uk_mod_news", "crisis_group", "ukraine_general_staff"}
)
UKRAINIAN_SOURCES = frozenset({"kyiv_independent", "ukrinform_en", "pravda_ua_en"})
RUSSIAN_SOURCES = frozenset(
    {
        "meduza_en",
        "meduza_ru",
        "mediazona_ru",
        "insider_ru",
        "interfax_ru",
        "tass_en",
        "russia_mfa_ru",
        "belta_ru",
    }
)

# Items filed under Russia or arriving from worldwide feeds must name the war.
_WAR_TERMS = re.compile(
    r"(?<![\w-])(?:Ukrain(?:e|ian|ians)|Kyiv|Kiev|Zelensk(?:y|yy|iy)|Donetsk|Luhansk|"
    r"Zaporizh(?:zhia|ia)|Kherson|Kharkiv|Crimea(?:n)?|Sumy|Dnipro|Odesa|Pokrovsk|"
    r"Kursk|Belgorod|frontline|front line)(?![\w-])",
    re.IGNORECASE,
)


def update_group(source_id: str) -> UpdateGroup:
    if source_id in ASSESSMENT_SOURCES:
        return UpdateGroup.ASSESSMENTS
    if source_id in UKRAINIAN_SOURCES:
        return UpdateGroup.UKRAINIAN
    if source_id in RUSSIAN_SOURCES:
        return UpdateGroup.RUSSIAN
    return UpdateGroup.INTERNATIONAL


def event_text(event: Event) -> str:
    return " ".join(part for part in (event.title, event.title_en, event.summary) if part)


def concerns_war(event: Event) -> bool:
    """Ukrainian sources and Ukraine-filed items pass; everything else must name the war."""
    if event.source_id in UKRAINIAN_SOURCES or event.source_id in ASSESSMENT_SOURCES:
        return event.source_id != "crisis_group" or _named(event)
    if event.country_iso == "UA":
        return True
    return _named(event)


def _named(event: Event) -> bool:
    return _WAR_TERMS.search(event_text(event)[:MAX_RELEVANCE_TEXT]) is not None
