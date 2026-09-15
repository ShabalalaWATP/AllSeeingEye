"""Public CTI publisher feeds verified with bounded requests on 12 and 13 September 2026.

Official feed directories: ncsc.gov.uk/information/rss-feeds,
cloud.google.com/blog/topics/threat-intelligence, cyber.gov.au's social media
community page, cisa.gov/cybersecurity-advisories, cert.gov.ua, cyber.gc.ca,
cert.ssi.gouv.fr and ic3.gov. The 13 September probes used the application's own
user agent; CISA's advisory feed answered 200 that day after an earlier 403. From
15 September 2026 the CISA and ACSC feeds refuse this client; rss_access.py defers them.
Candidates that answered 403 or 404 (ENISA news, WeLiveSecurity, CCDCOE, SSSCIP,
NCSC Ireland, Google TAG) were left out until their feed addresses are confirmed.
"""

from dataclasses import replace

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.feeds.rss_seeds import RssSeed, seed
from ase.domain.events import Category, Credibility, Reliability

_BASE = RssOptions(
    subtype="threat_report",
    tags=frozenset({"cyber_publication", "headlines_only"}),
    credibility=Credibility.CANNOT_BE_JUDGED,
    rationale="Publisher threat reporting; claims and attribution remain unassessed.",
    headlines_only=True,
    newest_first=True,
)
_OFFICIAL = replace(_BASE, tags=_BASE.tags | {"official_issuer", "interested_party"})
_VENDOR = replace(_BASE, tags=_BASE.tags | {"security_vendor", "interested_party"})
_COMMUNITY = replace(_BASE, tags=_BASE.tags | {"community_research"})
_ADVISORY = replace(_OFFICIAL, subtype="advisory")
_NEWS = replace(
    _BASE,
    subtype="news_report",
    tags=_BASE.tags | {"specialist_outlet"},
    rationale="Specialist cyber news reporting; claims and attribution remain unassessed.",
)
_TERMS = (
    "Publisher RSS terms apply. Headlines, dates, attribution and links only; no full article, "
    "malware, indicators or imagery retained. Public access does not establish commercial "
    "reuse permission. Publisher location is not incident geography."
)


def _row(
    key: str,
    name: str,
    organisation: str,
    url: str,
    homepage: str,
    options: RssOptions,
    *,
    language: str = "en",
) -> RssSeed:
    return seed(
        f"cyber_{key}",
        name,
        organisation,
        Category.CYBER,
        url,
        Reliability.F,
        30,
        options,
        homepage=homepage,
        licence_note=_TERMS,
        language=language,
        flags=options.tags - {"cyber_publication", "headlines_only"},
    )


CYBER_SEEDS: tuple[RssSeed, ...] = (
    _row(
        "ncsc_reports",
        "UK NCSC threat reports",
        "UK National Cyber Security Centre",
        "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml",
        "https://www.ncsc.gov.uk/section/keep-up-to-date/threat-reports",
        _OFFICIAL,
    ),
    _row(
        "ncsc_news",
        "UK NCSC news and threat statements",
        "UK National Cyber Security Centre",
        "https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml",
        "https://www.ncsc.gov.uk/section/keep-up-to-date/news",
        _ADVISORY,
    ),
    _row(
        "microsoft_threat_intelligence",
        "Microsoft Threat Intelligence",
        "Microsoft",
        "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/feed/",
        "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/",
        _VENDOR,
    ),
    _row(
        "cisco_talos",
        "Cisco Talos threat intelligence",
        "Cisco",
        "https://blog.talosintelligence.com/rss/",
        "https://blog.talosintelligence.com/",
        _VENDOR,
    ),
    _row(
        "google_threat_intelligence",
        "Google Threat Intelligence and Mandiant",
        "Google",
        "https://feeds.feedburner.com/threatintelligence/pvexyqv7v0v",
        "https://cloud.google.com/blog/topics/threat-intelligence",
        _VENDOR,
    ),
    _row(
        "cert_eu",
        "CERT-EU threat intelligence",
        "CERT-EU",
        "https://cert.europa.eu/publications/threat-intelligence-rss",
        "https://cert.europa.eu/publications/threat-intelligence",
        _OFFICIAL,
    ),
    _row(
        "acsc_advisories",
        "Australia ACSC advisories",
        "Australian Signals Directorate",
        "https://www.cyber.gov.au/rss/advisories",
        "https://www.cyber.gov.au/about-us/view-all-content/advisories",
        _ADVISORY,
    ),
    _row(
        "cisa_advisories",
        "US CISA cybersecurity and ICS advisories",
        "US Cybersecurity and Infrastructure Security Agency",
        "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "https://www.cisa.gov/news-events/cybersecurity-advisories",
        _ADVISORY,
    ),
    _row(
        "cert_ua",
        "CERT-UA incident and threat reports",
        "Government Computer Emergency Response Team of Ukraine",
        "https://cert.gov.ua/api/articles/rss",
        "https://cert.gov.ua/",
        _OFFICIAL,
        language="uk",
    ),
    _row(
        "cccs_alerts",
        "Canadian Centre for Cyber Security alerts and advisories",
        "Communications Security Establishment Canada",
        "https://www.cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories&lang=en",
        "https://www.cyber.gc.ca/en/alerts-advisories",
        _ADVISORY,
    ),
    _row(
        "cert_fr",
        "CERT-FR alerts and advisories",
        "French National Cybersecurity Agency (ANSSI)",
        "https://www.cert.ssi.gouv.fr/feed/",
        "https://www.cert.ssi.gouv.fr/",
        _ADVISORY,
        language="fr",
    ),
    _row(
        "ic3_psa",
        "FBI IC3 public service announcements",
        "US Federal Bureau of Investigation",
        "https://www.ic3.gov/PSA/RSS",
        "https://www.ic3.gov/PSA",
        _ADVISORY,
    ),
    _row(
        "sans_isc",
        "SANS Internet Storm Center diaries",
        "SANS Internet Storm Center",
        "https://isc.sans.edu/rssfeed.xml",
        "https://isc.sans.edu/",
        _COMMUNITY,
    ),
    _row(
        "unit42",
        "Palo Alto Networks Unit 42 research",
        "Palo Alto Networks",
        "https://unit42.paloaltonetworks.com/feed/",
        "https://unit42.paloaltonetworks.com/",
        _VENDOR,
    ),
    _row(
        "the_record",
        "The Record from Recorded Future News",
        "Recorded Future",
        "https://therecord.media/feed",
        "https://therecord.media/",
        _NEWS,
    ),
    _row(
        "bleeping_computer",
        "BleepingComputer security news",
        "BleepingComputer",
        "https://www.bleepingcomputer.com/feed/",
        "https://www.bleepingcomputer.com/",
        _NEWS,
    ),
)
