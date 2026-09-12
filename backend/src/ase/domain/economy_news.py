"""Reviewed economic feed identities and explicit topic tags, never map locations."""

import re
from typing import Literal

from ase.domain.events import Event

EconomyRegion = Literal["WORLD", "GB", "US", "RU", "CN", "IR"]
PublisherViewpoint = Literal["official_issuer", "state_aligned", "publisher"]

ECONOMIC_NEWS_IDS = (
    "economic_bbc_business",
    "economic_guardian_business",
    "economic_bank_england",
    "economic_hm_treasury",
    "economic_federal_reserve",
    "economic_bank_russia",
    "economic_scmp_china",
    "economic_cgtn_business",
    "economic_tehran_times",
)

_TOPIC_REMIT = {
    "economic_bank_england": "GB",
    "economic_hm_treasury": "GB",
    "economic_federal_reserve": "US",
    "economic_bank_russia": "RU",
    "economic_scmp_china": "CN",
    "economic_tehran_times": "IR",
}
_COUNTRIES = {
    "GB": r"\b(?:UK|U\.K\.|Britain|British|United Kingdom|Bank of England|FTSE|sterling)\b",
    "US": r"\b(?:(?-i:US|U\.S\.|USA)|United States|American|Federal Reserve|Wall Street|S&P 500)\b",
    "RU": r"\b(?:Russia|Russian|rouble|ruble|Bank of Russia)\b",
    "CN": r"\b(?:China|Chinese|Beijing|renminbi|yuan|Shanghai|PBOC)\b",
    "IR": r"\b(?:Iran|Iranian|Tehran|rial)\b",
}
_PATTERNS = {code: re.compile(pattern, re.IGNORECASE) for code, pattern in _COUNTRIES.items()}


def economic_regions(event: Event) -> tuple[str, ...]:
    """A feed's declared subject or explicit headline mention, not issuer nationality."""
    original = event.source_id.removeprefix("research_publisher_")
    text = f"{event.title} {event.title_en or ''}"
    return tuple(
        code
        for code, pattern in _PATTERNS.items()
        if _TOPIC_REMIT.get(original) == code or pattern.search(text)
    )


def economic_viewpoint(event: Event) -> PublisherViewpoint:
    if "official_issuer" in event.tags:
        return "official_issuer"
    if "state_aligned" in event.tags or "state_controlled" in event.tags:
        return "state_aligned"
    return "publisher"
