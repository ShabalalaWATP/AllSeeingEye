"""Bounded keyword lenses over cyber reporting. A lens is a text match, never attribution."""

from __future__ import annotations

import re
from enum import StrEnum

MAX_THEME_TEXT = 3_000
UKRAINE_SOURCE_IDS = frozenset({"cyber_cert_ua"})
UK_SOURCE_PREFIX = "cyber_ncsc_"


class CyberTheme(StrEnum):
    NATION_STATE = "nation_state"
    NATO_ALLIES = "nato_allies"
    UK_INFRASTRUCTURE = "uk_infrastructure"
    UKRAINE = "ukraine"
    GNSS_INTERFERENCE = "gnss_interference"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"


def _words(*terms: str, flags: int = re.IGNORECASE) -> re.Pattern[str]:
    return re.compile(r"(?<![\w-])(?:" + "|".join(terms) + r")(?![\w-])", flags)


_STATE_ADJECTIVES = (
    r"(?:russian|chinese|iranian|north korean|dprk|prc|kremlin|beijing|tehran|pyongyang)"
)
_NATION_STATE = _words(
    r"state[- ]sponsored",
    r"state[- ]backed",
    r"state[- ]aligned",
    r"state[- ]linked",
    r"state[- ]affiliated",
    r"nation[- ]states?",
    r"government[- ](?:backed|sponsored|linked)",
    r"cyber[- ]?espionage",
    r"espionage",
    r"intelligence (?:service|services|agency|agencies|officers?)",
    r"military intelligence",
    _STATE_ADJECTIVES
    + r"[- ](?:state|government|hackers|actors?|groups?|threat|cyber|espionage|intelligence|"
    r"military|linked|backed|aligned|nexus|operatives?|campaign)",
)
_NATION_STATE_ACRONYMS = _words(
    r"GRU", r"FSB", r"SVR", r"MSS", r"PLA", r"IRGC", r"MOIS", r"APT\d{1,3}", r"UNC\d{3,5}", flags=0
)
_VENDOR_FAMILIES = re.compile(
    r"\b[A-Z][a-z]+ (?:Typhoon|Blizzard|Sandstorm|Sleet|Bear|Panda|Kitten|Chollima)\b"
)
_NATO_DIRECT = _words(
    r"NATO",
    r"North Atlantic (?:Treaty|Alliance|Council)",
    r"allied (?:governments?|forces|nations|militaries|defen[cs]e|command|partners)",
    r"the alliance",
    r"Pentagon",
    r"Department of Defen[cs]e",
    r"Ministry of Defen[cs]e",
    r"defen[cs]e (?:ministry|ministries|department|sector|industry|contractors?|industrial base)",
    r"armed forces",
    r"military (?:networks?|systems?|personnel|bases?|command|units?|organi[sz]ations?)",
    r"Bundeswehr",
    r"European (?:Union|Commission|Parliament|External Action Service)",
    r"EU (?:institutions?|agencies|member states?|bodies)",
    r"Five Eyes",
    r"Eastern flank",
    r"Baltics?(?: states?| region| sea| countries)?",
    r"Nordic(?:s| countries| region)",
)
_NATO_ACRONYMS = _words(r"US", r"USA", r"U\.S\.", r"UK", r"U\.K\.", r"EU", flags=0)
_NATO_MEMBERS = _words(
    r"Albania(?:n)?",
    r"Belgi(?:um|an)",
    r"Bulgaria(?:n)?",
    r"Canad(?:a|ian)",
    r"Croatia(?:n)?",
    r"Czech(?:ia| Republic)?",
    r"Denmark",
    r"Danish",
    r"Estonia(?:n)?",
    r"Finland",
    r"Finnish",
    r"France",
    r"French",
    r"German(?:y)?",
    r"Greece",
    r"Greek",
    r"Hungar(?:y|ian)",
    r"Iceland(?:ic)?",
    r"Ital(?:y|ian)",
    r"Latvia(?:n)?",
    r"Lithuania(?:n)?",
    r"Luxembourg",
    r"Montenegr(?:o|in)",
    r"Netherlands",
    r"Dutch",
    r"North Macedonia(?:n)?",
    r"Norw(?:ay|egian)",
    r"Poland",
    r"Polish",
    r"Portug(?:al|uese)",
    r"Romania(?:n)?",
    r"Slovak(?:ia|ian)?",
    r"Slovenia(?:n)?",
    r"Spain",
    r"Spanish",
    r"Sweden",
    r"Swedish",
    r"Turk(?:ey|ish|iye)",
    r"Türkiye",
    r"United Kingdom",
    r"Britain",
    r"British",
    r"United States",
    r"U\.S\.",
    r"US (?:government|federal|agencies|military)",
    r"American",
)
_INCIDENT = _words(
    r"attack(?:s|ed|ing)?",
    r"target(?:s|ed|ing)?",
    r"breach(?:es|ed)?",
    r"campaign(?:s)?",
    r"intrusion(?:s)?",
    r"compromise[sd]?",
    r"hack(?:s|ed|ing|ers)?",
    r"disrupt(?:s|ed|ion|ive)?",
    r"DDoS",
    r"ransomware",
    r"espionage",
    r"phishing",
    r"malware",
    r"wiper",
    r"sabotage",
    r"government",
    r"ministry",
    r"parliament",
    r"election(?:s)?",
    r"infrastructure",
)
_UK = _words(
    r"UK",
    r"U\.K\.",
    r"United Kingdom",
    r"Britain",
    r"British",
    r"England",
    r"Scotland",
    r"Scottish",
    r"Wales",
    r"Welsh",
    r"Northern Ireland",
    r"NHS",
    r"NCSC",
    r"Ofgem",
    r"Ofcom",
    r"National Grid",
    r"Thames Water",
    r"Royal Mail",
    r"HMRC",
    r"GCHQ",
    r"Whitehall",
    r"Westminster",
    r"Home Office",
    r"Cabinet Office",
    r"Ministry of Defence",
    r"MoD",
    r"London",
    r"Manchester",
    r"Birmingham",
    r"Glasgow",
    r"Edinburgh",
    r"Belfast",
    r"Cardiff",
    r"Transport for London",
    r"TfL",
    r"Network Rail",
    r"Sellafield",
    r"Heathrow",
    r"Gatwick",
    r"British Library",
    r"Jaguar Land Rover",
    r"Marks (?:&|and) Spencer",
)
_INFRASTRUCTURE = _words(
    r"critical (?:national )?infrastructure",
    r"CNI",
    r"operational technology",
    r"industrial control(?: systems?)?",
    r"SCADA",
    r"ICS",
    r"OT",
    r"PLCs?",
    r"HMIs?",
    r"power grid",
    r"electricity (?:grid|network|supply)",
    r"grid operator",
    r"substations?",
    r"water (?:utility|utilities|treatment|systems?|sector|supply|companies|company)",
    r"wastewater",
    r"pipelines?",
    r"energy (?:sector|company|companies|provider|firm|grid|utility)",
    r"nuclear",
    r"oil and gas",
    r"rail(?:way)? (?:network|operator|services?)",
    r"airports?",
    r"port (?:authority|operator)",
    r"healthcare",
    r"hospitals?",
    r"health service",
    r"NHS",
    r"telecom(?:s|munications)?(?: operator| provider| network| sector)?",
    r"satellite (?:communications?|networks?|operators?|terminals?)",
    r"dams?",
    r"utilit(?:y|ies)",
    r"transport (?:network|operator|systems?)",
    r"emergency services",
    r"Siemens",
    r"Schneider Electric",
    r"Rockwell",
    r"Honeywell",
    r"AVEVA",
    r"Mitsubishi Electric",
    r"Hitachi Energy",
    r"ABB",
    r"Emerson",
    r"Moxa",
    r"Phoenix Contact",
    r"Delta Electronics",
    r"Johnson Controls",
    r"Yokogawa",
    r"Ovarro",
    r"Advantech",
)
_UKRAINE = _words(
    r"Ukrain(?:e|ian|ians)",
    r"Kyiv",
    r"Kiev",
    r"Kharkiv",
    r"Odes[as]a?",
    r"Lviv",
    r"Dnipro",
    r"Zaporizh(?:zhia|ia)",
    r"Kherson",
    r"Crimea(?:n)?",
    r"Donbas",
    r"Donetsk",
    r"Luhansk",
    r"Mykolaiv",
    r"Sumy",
    r"Chernihiv",
    r"CERT-UA",
    r"UAC-\d{4}",
    r"Gamaredon",
    r"Sandworm",
    r"Armageddon",
    r"Ukrenergo",
    r"Kyivstar",
    r"Zelensky",
    r"Zelenskyy",
)
_GNSS = _words(
    r"GNSS",
    r"GPS",
    r"Galileo",
    r"GLONASS",
    r"BeiDou",
    r"satnav",
    r"sat-nav",
    r"PNT",
    r"positioning, navigation and timing",
    r"navigation interference",
    r"jamm(?:ing|ed|ers?)",
    r"navigation warfare",
    r"NAVWAR",
)
_SPOOFING = _words(r"spoof(?:ing|ed|er|ers)?")
_NAVIGATION = _words(
    r"navigation",
    r"aircraft",
    r"aviation",
    r"flights?",
    r"ships?",
    r"vessels?",
    r"maritime",
    r"airspace",
    r"receivers?",
    r"signals?",
)


def _has(pattern: re.Pattern[str], text: str) -> bool:
    return pattern.search(text) is not None


def classify_cyber_themes(
    text: str,
    *,
    source_id: str = "",
    country_iso: str | None = None,
    connectivity_signal: bool = False,
) -> tuple[CyberTheme, ...]:
    """Deterministic lenses over bounded headline text plus explicit source metadata.

    A match means the text or metadata mentions the topic. It never establishes who
    acted, whether an incident occurred, or that an unmatched record is unrelated.
    """
    sample = text[:MAX_THEME_TEXT]
    themes: list[CyberTheme] = []
    if (
        _has(_NATION_STATE, sample)
        or _has(_NATION_STATE_ACRONYMS, sample)
        or _has(_VENDOR_FAMILIES, sample)
    ):
        themes.append(CyberTheme.NATION_STATE)
    member = _has(_NATO_MEMBERS, sample) or _has(_NATO_ACRONYMS, sample)
    if _has(_NATO_DIRECT, sample) or (member and _has(_INCIDENT, sample)):
        themes.append(CyberTheme.NATO_ALLIES)
    uk_context = _has(_UK, sample) or country_iso == "GB" or source_id.startswith(UK_SOURCE_PREFIX)
    infrastructure = _has(_INFRASTRUCTURE, sample)
    if uk_context and (infrastructure or (country_iso == "GB" and connectivity_signal)):
        themes.append(CyberTheme.UK_INFRASTRUCTURE)
    if _has(_UKRAINE, sample) or country_iso == "UA" or source_id in UKRAINE_SOURCE_IDS:
        themes.append(CyberTheme.UKRAINE)
    if _has(_GNSS, sample) or (_has(_SPOOFING, sample) and _has(_NAVIGATION, sample)):
        themes.append(CyberTheme.GNSS_INTERFERENCE)
    if infrastructure:
        themes.append(CyberTheme.CRITICAL_INFRASTRUCTURE)
    return tuple(themes)
