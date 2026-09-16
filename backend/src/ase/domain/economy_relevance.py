"""Whether one headline is genuinely about the economy, decided by readable rules.

No model call and no network: the same headline always produces the same verdict and the
same explanation, so an excluded story can be argued with. The rules are deliberately
blunt.

1. A feature framing ("here's how we got through the first few days") is never economic
   reporting, whoever published it.
2. An official economic issuer (a central bank, a statistics office, a trade body) is on
   remit by the nature of its feed, so its releases pass without a lexicon hit.
3. Everything else needs at least one CORE subject-matter phrase. Supporting phrases
   (companies, institutions, measurement words), a declared country remit and figures in
   the headline raise the score and the tier, but they can never carry a headline on
   their own: "Complaints to watchdog about water firms jump 84%" has a company word and
   a percentage and is still not economic reporting.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ase.domain.economy_lexicon import CORE_THEMES, SOFT_FEATURE_PHRASES, SUPPORTING_THEMES

#: Ordered best first; the panel ranks official data releases above general coverage.
TIER_LABELS = ("official_release", "market_reporting", "general_coverage")
_FIGURES = re.compile(
    r"(?:\d+(?:[.,]\d+)*\s?%)|(?:[$£€¥]\s?\d)|(?:\b\d+(?:[.,]\d+)?\s?(?:bn|billion|"
    r"trillion|tn|million|m|basis points|bps)\b)|(?:\b\d+(?:[.,]\d+)?\s?per cent\b)",
    re.IGNORECASE,
)


def _compile(phrases: tuple[str, ...]) -> re.Pattern[str]:
    parts = [
        rf"{re.escape(phrase[:-1])}\w*" if phrase.endswith("*") else rf"{re.escape(phrase)}\b"
        for phrase in phrases
    ]
    return re.compile(rf"\b(?:{'|'.join(parts)})", re.IGNORECASE)


def _index(themes: Mapping[str, tuple[str, ...]]) -> Mapping[str, re.Pattern[str]]:
    return {label: _compile(phrases) for label, phrases in themes.items()}


_CORE = _index(CORE_THEMES)
_SUPPORTING = _index(SUPPORTING_THEMES)
_SOFT_FEATURE = _compile(SOFT_FEATURE_PHRASES)


@dataclass(frozen=True, slots=True)
class EconomicRelevance:
    """One explainable verdict: kept or not, why, and how prominently to show it."""

    passed: bool
    tier: int
    score: int
    reason: str
    themes: tuple[str, ...]


def assess_relevance(
    title: str, *, official: bool = False, remit: bool = False
) -> EconomicRelevance:
    """Judge a headline. `official` is an official economic issuer's own release; `remit`
    is a feed with a declared country economic remit."""
    text = " ".join(title.split())
    if _SOFT_FEATURE.search(text):
        return EconomicRelevance(
            False, 2, 0, "Feature or lifestyle framing, not economic reporting", ()
        )
    core = tuple(label for label, pattern in _CORE.items() if pattern.search(text))
    supporting = tuple(label for label, pattern in _SUPPORTING.items() if pattern.search(text))
    figures = bool(_FIGURES.search(text))
    score = 2 * len(core) + len(supporting) + int(figures) + int(remit) + 2 * int(official)
    if not core and not official:
        return EconomicRelevance(
            False, 2, score, "No economic subject matter in the headline", supporting
        )
    return EconomicRelevance(
        True, _tier(official, core, figures), score, _reason(official, core, figures), core
    )


def _tier(official: bool, core: tuple[str, ...], figures: bool) -> int:
    if official and (core or figures):
        return 0
    if core and (figures or len(core) > 1):
        return 1
    return 2


def _reason(official: bool, core: tuple[str, ...], figures: bool) -> str:
    subject = ", ".join(core)
    if official:
        lead = f"Official economic issuer release on {subject}" if core else (
            "Official economic issuer release"
        )
    else:
        lead = f"Economic subject matter: {subject}"
    return f"{lead}; figures cited" if figures else lead
