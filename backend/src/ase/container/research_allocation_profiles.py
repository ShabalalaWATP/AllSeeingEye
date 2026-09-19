"""Reviewed E01 purpose metadata for the implemented research routes.

Reviewed against local provider/seed contracts on 2026-09-14, not live availability.
Terms express useful subject coverage, not evidence returned or verified geography.
Every ID is explicit: a new provider needs review before allocation can admit it.
"""

from collections.abc import Mapping
from functools import partial
from types import MappingProxyType

from ase.application.research.source_allocation_types import AllocationProfile
from ase.container.research_e03_allocation_profiles import e03_allocation_profiles

PROFILE_VERSION = "ase-research-allocation-profiles-v1"
REVIEW_DATE = "2026-09-14"
NEWS = (
    "politics|government|diplomacy|conflict war|military|security|attacks|economy|trade|energy|"
    "migration|humanitarian|elections|sanctions|protests|technology|climate|health"
)
DEFENCE = "defence defense|military|security|warfare|drone drones|procurement|Ukraine|NATO|weapons"
CYBER = (
    "cyber cybersecurity|vulnerability vulnerabilities|exploitation exploits|malware|ransomware|"
    "phishing|intrusion|espionage|campaign|network|patch|attack attacks"
)
ECONOMY = (
    "economy economic|inflation|interest rates|growth|employment|monetary|banking|financial|"
    "trade|energy|GDP|business|investment"
)
COMPANY = "company corporate|registry|identity|ownership|control|officers|parent|business|LEI"
TECHNICAL = "domain|DNS|infrastructure|network|registration|registrar|hosting|ownership|mail"


# One reviewed statement per provider family, read top to bottom as a register.
def research_allocation_profiles() -> Mapping[str, AllocationProfile]:  # noqa: PLR0915
    """Return immutable purpose profiles, with no settings, query text or external IO."""
    result: dict[str, AllocationProfile] = {}

    def add(
        ids: str,
        terms: str,
        note: str,
        *,
        prefix: str = "research_publisher_",
        countries: tuple[str, ...] = (),
        primary: bool = False,
        local: bool = False,
    ) -> None:
        for suffix in ids.split():
            source_id = prefix + suffix
            if source_id in result:
                raise ValueError("Duplicate reviewed allocation profile")
            result[source_id] = AllocationProfile(
                tuple(terms.split("|")), f"{REVIEW_DATE}: {note}", countries, primary, local
            )

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

    # Primary means attributable records/measurements, not verified claims.
    record = partial(add, prefix="")
    record(
        "research-uk-parliament",
        DEFENCE + "|parliament|policy|government|civilian|aid",
        "Parliament question and answer text; attributed assertions, not established findings.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-world-bank",
        ECONOMY + "|statistics|indicator|population|poverty|annual|data",
        "World Bank indicator values and units; current annual series, not historical vintages.",
        primary=True,
    )
    record(
        "research-ons-cpih",
        "ONS|CPIH|inflation|consumer|prices|index|monthly|statistics",
        "ONS monthly index values; explicit version, no latest-vintage or publication-date claim.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-cloudflare-radar-layer3 research-cloudflare-radar-layer7",
        "Cloudflare|Radar|DDoS|network|traffic|attack attacks|distribution|target|layer3|layer7",
        "Cloudflare distributions; provider denominators, no incident or attribution proof.",
        primary=True,
    )
    record(
        "research-sec-submissions research-sec-company-directory",
        COMPANY + "|SEC|filing|ticker|accounts",
        "SEC filing/directory metadata; underlying filings are not acquired as primary passages.",
    )
    record(
        "research-companies-house research-companies-house-officers research-companies-house-psc",
        COMPANY,
        "Registry fields and assertions; no verified beneficial ownership or historical snapshot.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-gleif-profile research-gleif-direct-parent research-gleif-ultimate-parent",
        COMPANY,
        "GLEIF assertions and accounting-consolidation links, not verified beneficial ownership.",
        primary=True,
    )
    record(
        "research-rdap",
        TECHNICAL,
        "Direct registry RDAP fields; registration does not establish operational ownership.",
        primary=True,
    )
    record(
        "research-dns-a research-dns-aaaa research-dns-mx research-dns-ns",
        TECHNICAL,
        "Current resolver observations; no historical infrastructure or identity/ownership proof.",
        primary=True,
    )
    record(
        "research-certificate-transparency",
        TECHNICAL + "|certificate|TLS",
        "Third-party certificate index; not direct service observation or ownership evidence.",
    )
    record(
        "research-contracts-finder",
        "procurement|contract|tender|award|supplier|spending|drone drones|defence",
        "Published notice assertions; no verified delivery or acquisition of linked originals.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-designations-uksl research-designations-ofac_sdn",
        COMPANY + "|sanctions|designation|asset|restriction",
        "Imported list records; provenance and identity remain unverified, no absence clearance.",
        primary=True,
    )
    record(
        "research-asset-register",
        "cable cables|data centre datacentre|nuclear reactor|semiconductor chip fab|"
        "power station grid|refinery pipeline terminal|ground station teleport|"
        "infrastructure site facility|connectivity outage blackout",
        "Packaged map registers, gated by a reviewed asset phrase; not current site state.",
    )
    record(
        "research-aiddata-projects",
        "development|aid|China|loan|finance|infrastructure|project|energy|commitment",
        "Research project catalogue, not original loan agreements or disbursement evidence.",
    )
    record(
        "research-ooni-aggregate",
        "internet|connectivity|censorship|blocking|outage|network|OONI|measurement",
        "OONI measurements; anomalies do not establish interference, cause or attribution.",
        primary=True,
    )
    record(
        "research-openalex research-crossref",
        "academic|scholarly|paper|publication|journal|citation|research|study|science",
        "Overlapping scholarly metadata discovery, not paper acquisition.",
    )
    record(
        "research-usgs-area",
        "earthquake|seismic|hazard|magnitude|tremor|disaster",
        "USGS catalogue measurements; bounded geometry/time coverage and revision limits.",
        primary=True,
    )
    record(
        "research-osm-features",
        "church|mosque|station|bridge|stadium|airport|harbour|power plant|dam|hospital|"
        "tower|lighthouse|factory|mine|prison|military|river|lake|monument|castle|embassy|"
        "border|landmark|building",
        "OpenStreetMap features of the named kinds inside the drawn area; current map state.",
    )
    record(
        "research-eonet-area",
        "hazard|wildfire|storm|volcano|flood|disaster|weather",
        "NASA aggregation of hazard records; upstream origins and coverage need review.",
    )
    record(
        "research-openaq-area",
        "air|pollution|quality|particulate|environment|emissions",
        "Aggregated air-quality measurements; underlying stations and origins require review.",
    )
    record(
        "research-copernicus-footprints",
        "satellite|Sentinel|acquisition|footprint|imagery|observation",
        "Catalogue acquisition footprints only; no imagery or incident interpretation.",
        primary=True,
    )
    record(
        "research-retained-area-feeds",
        NEWS + "|hazard|satellite|vessel|flight|observation|area",
        "Mixed retained observations; source, geometry and dates need checks, no backfill.",
    )
    result.update(e03_allocation_profiles(REVIEW_DATE))
    return MappingProxyType(dict(sorted(result.items())))
