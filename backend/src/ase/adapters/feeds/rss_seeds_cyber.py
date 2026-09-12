"""Public CTI publisher feeds verified with bounded requests on 12 September 2026.

Official feed directories: ncsc.gov.uk/information/rss-feeds,
cloud.google.com/blog/topics/threat-intelligence and cyber.gov.au's social media
community page. CISA RSS returned 403; its working KEV API remains separate.
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
_ADVISORY = replace(_OFFICIAL, subtype="advisory")
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
)
