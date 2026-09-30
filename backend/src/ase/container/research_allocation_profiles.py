"""Reviewed E01 purpose metadata for the implemented research routes.

Reviewed against local provider/seed contracts on 2026-09-14, not live availability.
Terms express useful subject coverage, not evidence returned or verified geography.
Every ID is explicit: a new provider needs review before allocation can admit it.
"""

from collections.abc import Mapping
from functools import partial
from types import MappingProxyType

from ase.application.research.source_allocation_types import AllocationProfile
from ase.container.research_allocation_model import (
    CYBER,
    DEFENCE,
    ECONOMY,
    NEWS,
    PROFILE_VERSION,
    REVIEW_DATE,
    add_profile,
)
from ase.container.research_bridge_allocation_profiles import e03_allocation_profiles
from ase.container.research_record_allocation_profiles import record_allocation_profiles

__all__ = ["PROFILE_VERSION", "REVIEW_DATE", "research_allocation_profiles"]


# One reviewed statement per provider family, read top to bottom as a register.
def research_allocation_profiles() -> Mapping[str, AllocationProfile]:
    """Return immutable purpose profiles, with no settings, query text or external IO."""
    result: dict[str, AllocationProfile] = {}

    add = partial(add_profile, result)

    add(
        "ar de en es fr hi ja ko pt ru uk zh-cn zh-tw",
        NEWS,
        "Configured Google editions expose metadata, not publisher, language or origin proof.",
        prefix="research_google_news_",
    )
    add(
        "bbc_world dw_world france24_en aljazeera_en guardian_world lemonde_en",
        NEWS,
        "International feed titles only; no original passages or geographic guarantee.",
    )
    for ids, country, terms in (
        ("scmp_news cgtn_china", "CN", "China|Chinese"),
        ("nikkei_asia", "JP", "Asia|Japan"),
        ("times_of_israel", "IL", "Israel|Gaza|Iran"),
        ("anadolu_en", "TR", "Turkey|Türkiye|Syria"),
        ("dawn", "PK", "Pakistan|Afghanistan"),
        ("meduza_en tass_en", "RU", "Russia|Ukraine|drone drones"),
        ("pravda_ua_en kyiv_independent", "UA", "Ukraine|Russia|drone drones"),
    ):
        add(
            ids,
            NEWS + "|" + terms,
            "Regional editorial focus; headline metadata, not verified incidents.",
            countries=(country,),
        )
    add(
        "bellingcat",
        DEFENCE + "|investigation|verification|open source|civilian",
        "Investigation feed titles; supporting originals and methods are not acquired.",
    )
    add(
        "gov_uk_mod_news",
        DEFENCE,
        "MOD announcements are attributed positions; this route retains headlines only.",
        countries=("GB",),
    )
    add(
        "us_dod_news",
        DEFENCE,
        "Defence Department statements through headlines, not acquired primary passages.",
        countries=("US",),
    )
    for ids, country in (("gov_uk_fcdo_news gov_uk_number_10", "GB"), ("whitehouse_news", "US")):
        add(
            ids,
            "government|policy|diplomacy|sanctions|security|Ukraine|Russia|trade|aid",
            "Official announcement titles; no original passages are acquired.",
            countries=(country,),
        )
    for ids, country in (("gov_uk_travel_advice", "GB"), ("us_state_travel_advisories", "US")):
        add(
            ids,
            "travel|advisory|safety|security|consular|evacuation|border",
            "Travel-advice headline changes; complete current guidance was not retrieved.",
            countries=(country,),
        )
    add(
        "gov_uk_home_office",
        "migration|immigration|border|security|policing|crime|asylum",
        "Home Office announcement titles, not operational records.",
        countries=("GB",),
    )
    add(
        "russia_mfa_ru",
        "Russia|Ukraine|diplomacy|sanctions|security|МИД|Россия|Украина",
        "Russian-language ministry statements; attributed state positions, headlines only.",
        countries=("RU",),
        local=True,
    )
    add(
        "un_news un_press reliefweb_updates crisis_group",
        "humanitarian|conflict|civilian|displacement|refugee|aid|hunger|ceasefire|peace|Ukraine|Gaza",
        "Humanitarian feed titles; upstream claims and original reports require review.",
    )
    for ids, country in (
        ("economic_bank_england economic_hm_treasury economic_ons_releases", "GB"),
        (
            "economic_federal_reserve economic_bls_consumer_prices economic_bls_employment "
            "economic_bls_producer_prices economic_census_indicators economic_eia_energy",
            "US",
        ),
        ("economic_bank_russia economic_the_bell", "RU"),
        ("economic_scmp_china economic_cgtn_business", "CN"),
        ("economic_tehran_times", "IR"),
        ("economic_bank_japan", "JP"),
        ("economic_bank_canada", "CA"),
        ("economic_reserve_bank_india", "IN"),
    ):
        add(
            ids,
            ECONOMY,
            "Economic release headlines; no statistical series, units or vintages acquired.",
            countries=(country,),
        )
    add(
        "economic_bbc_business economic_guardian_business economic_economist_finance "
        "economic_dw_business economic_france24_business economic_intellinews",
        ECONOMY,
        "Business-news headline discovery, not a statistical dataset.",
    )
    add(
        "economic_ecb_press economic_bis_speeches economic_wto_news",
        ECONOMY,
        "Multilateral and central-bank release headlines; no statistical series acquired.",
    )
    for ids, country, extra in (
        ("cyber_cisa_advisories", "US", "ICS|industrial|appliance"),
        ("cyber_ncsc_news cyber_ncsc_reports", "GB", "advisory|guidance"),
        ("cyber_acsc_advisories", "AU", "advisory|guidance"),
        ("cyber_cccs_alerts", "CA", "advisory|guidance"),
        ("cyber_ic3_psa", "US", "fraud|scam|cybercrime"),
    ):
        add(
            ids,
            CYBER + "|" + extra,
            "Cyber advisory headlines; no KEV records or original technical passages.",
            countries=(country,),
        )
    add(
        "cyber_cert_eu",
        CYBER,
        "CERT-EU intelligence headline discovery; no original report passages.",
    )
    add(
        "cyber_cert_ua",
        CYBER + "|Ukraine|Україна|кібератаки",
        "CERT-UA Ukrainian publication route; headlines only and attributed claims.",
        countries=("UA",),
        local=True,
    )
    add(
        "cyber_cert_fr",
        CYBER + "|France|vulnérabilité|sécurité",
        "CERT-FR French publication route; headlines only and attributed claims.",
        countries=("FR",),
        local=True,
    )
    for ids, extra in (
        ("cyber_cisco_talos", "Cisco|appliance"),
        ("cyber_google_threat_intelligence", "Google|Mandiant"),
        ("cyber_microsoft_threat_intelligence", "Microsoft|Windows"),
        ("cyber_unit42", "Palo Alto|appliance"),
        ("cyber_sans_isc cyber_the_record cyber_bleeping_computer", "incident|research"),
    ):
        add(
            ids,
            CYBER + "|" + extra,
            "Vendor/community/news titles; original technical research is not acquired.",
        )
    for ids, country, extra, local in (
        (
            "meduza_ru mediazona_ru insider_ru interfax_ru",
            "RU",
            "Russia|Ukraine|drone drones|Россия|Украина",
            True,
        ),
        ("belta_ru", "BY", "Belarus|Россия|Беларусь", True),
        ("hrana_fa iranwire_fa", "IR", "Iran|human rights|ایران", True),
        ("hrana_en iranwire_en", "IR", "Iran|human rights", False),
        ("ukrinform_en", "UA", "Ukraine|drone drones|civilian|displacement", False),
        ("cdt_zh", "CN", "China|censorship|中国", False),
    ):
        add(
            ids,
            NEWS + "|" + extra,
            "Feed metadata; configured language is not detected language. CDT is an aggregator.",
            prefix="research_regional_",
            countries=(country,),
            local=local,
        )

    add(
        "telegram",
        DEFENCE + "|Russia|war|strikes|drone|missile|sanctions|cyber|Israel|Iran|protests",
        "Curated participant channels: governments, armed forces, state media and aligned "
        "commentators. One channel preview per request; claims, not corroboration.",
        prefix="research_social_",
    )
    add(
        "bluesky",
        "conflict war|military|drone drones|cyber|sanctions|economy|energy|humanitarian|"
        "disinformation|maritime|aviation|space|Ukraine|Russia|China|Taiwan|Israel|Iran|"
        "Korea|Africa|government|protests|technology|intelligence",
        "One aggregated curated-account route; phrases choose at most three public feeds, "
        "and no account, claim or location is verified.",
        prefix="research_social_",
    )
    add(
        "research-youtube",
        NEWS + "|video|footage|briefing|interview|analysis",
        "Platform-wide video search metadata; uploader claims, no channel or origin proof.",
        prefix="",
    )

    result.update(record_allocation_profiles())
    result.update(e03_allocation_profiles(REVIEW_DATE))
    return MappingProxyType(dict(sorted(result.items())))
