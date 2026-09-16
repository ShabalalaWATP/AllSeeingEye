"""Reviewed economic feed identities and explicit topic tags, never map locations."""

import re
from typing import Literal

from ase.domain.economy_relevance import EconomicRelevance, assess_relevance
from ase.domain.events import Event

EconomyRegion = Literal["WORLD", "GB", "US", "RU", "CN", "IR"]
PublisherViewpoint = Literal["official_issuer", "state_aligned", "publisher"]

ECONOMIC_NEWS_IDS = (
    "economic_bank_england",
    "economic_hm_treasury",
    "economic_ons_releases",
    "economic_federal_reserve",
    "economic_bls_consumer_prices",
    "economic_bls_employment",
    "economic_bls_producer_prices",
    "economic_census_indicators",
    "economic_eia_energy",
    "economic_ecb_press",
    "economic_bis_speeches",
    "economic_wto_news",
    "economic_bank_japan",
    "economic_bank_canada",
    "economic_reserve_bank_india",
    "economic_bank_russia",
    "economic_bbc_business",
    "economic_guardian_business",
    "economic_economist_finance",
    "economic_dw_business",
    "economic_france24_business",
    "economic_intellinews",
    "economic_the_bell",
    "economic_scmp_china",
    "economic_cgtn_business",
    "economic_tehran_times",
)

_TOPIC_REMIT = {
    "economic_bank_england": "GB",
    "economic_hm_treasury": "GB",
    "economic_ons_releases": "GB",
    "economic_federal_reserve": "US",
    "economic_bls_consumer_prices": "US",
    "economic_bls_employment": "US",
    "economic_bls_producer_prices": "US",
    "economic_census_indicators": "US",
    "economic_eia_energy": "US",
    "economic_bank_russia": "RU",
    "economic_the_bell": "RU",
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
    text = f"{event.title} {event.title_en or ''}"
    return tuple(
        code
        for code, pattern in _PATTERNS.items()
        if _TOPIC_REMIT.get(_feed_id(event)) == code or pattern.search(text)
    )


def economic_viewpoint(event: Event) -> PublisherViewpoint:
    if "official_issuer" in event.tags:
        return "official_issuer"
    if "state_aligned" in event.tags or "state_controlled" in event.tags:
        return "state_aligned"
    return "publisher"


def economic_relevance(event: Event) -> EconomicRelevance:
    """Whether this headline is economic reporting, with the reason kept for debugging."""
    return assess_relevance(
        f"{event.title} {event.title_en or ''}",
        official=economic_viewpoint(event) == "official_issuer",
        remit=_TOPIC_REMIT.get(_feed_id(event)) is not None,
    )


def _feed_id(event: Event) -> str:
    return event.source_id.removeprefix("research_publisher_")
