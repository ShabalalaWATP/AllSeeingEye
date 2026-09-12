"""Explicit cited cyber briefings through the normal private research pipeline."""

from ase.application.reports.request import ReportRequest
from ase.domain.cyber import CYBER_PUBLISHER_IDS, CyberWindowDays, cyber_window
from ase.domain.events import Category
from ase.domain.research import ResearchMode


def coverage_note(days: CyberWindowDays) -> str:
    return (
        f"A {int(days)} day cyber briefing, with a separate 24-hour refresh interval. "
        "Uses available retained cyber observations and selected publisher headline feeds. "
        "Publisher snapshots may not cover the whole period; full articles are not collected. "
        "Reference actor knowledge is historical context, not current activity or attribution."
    )


def cyber_briefing_request(days: CyberWindowDays = CyberWindowDays.TWO) -> ReportRequest:
    days = cyber_window(days)
    return ReportRequest(
        template_id="ask",
        question=(
            f"Write a {int(days)} day cyber threat intelligence briefing for the exact supplied "
            "reporting range. State the frozen start and end dates. Use clear headings: "
            "Executive overview; Main developments; Exploited vulnerabilities; Ransomware "
            "claims; Actor reporting; Connectivity observations; Defensive priorities; "
            "What to watch; Coverage and method. Start with a concise executive paragraph, "
            "then explain dated developments and their implications in short paragraphs. "
            "Use in-text citations to captured evidence and a reference list. Distinguish "
            "official advisories, vendor analysis, publisher reporting, criminal claims and "
            "inference. Headline-only evidence does not establish details from an unread "
            "article. A ransomware victim listing is an unverified claim, not a confirmed "
            "breach. Connectivity loss does not establish a cyberattack or its cause. "
            "A CISA KEV publication date means addition to the catalogue, not when exploitation "
            "began. Its due date is a remediation deadline with the authority's stated scope, "
            "not a universal deadline. Separate actor-name mentions and alias associations "
            "from independently supported attribution; do not infer country sponsorship "
            "from a name, language or victim location. Report observed feed counts as partial "
            "reporting volumes, never total attacks or prevalence. Missing records do not "
            "establish no activity. Describe source coverage, publication-date uncertainty, "
            "stale inputs and missing publisher archives. Keep recommendations defensive "
            "and grounded in cited advisories, including patch prioritisation and verification. "
            "Do not generate exploit steps, conduct scanning or invent indicators."
        ),
        categories=(Category.CYBER,),
        window_hours=int(days) * 24,
        research_mode=ResearchMode.DETAILED,
        research_source_ids=tuple(f"research_publisher_{key}" for key in CYBER_PUBLISHER_IDS),
        research_terms=(
            "cyber",
            "threat",
            "vulnerability",
            "ransomware",
            "malware",
            "exploit",
            "attack",
            "security",
            "phishing",
            "CVE",
            "advisory",
            "campaign",
        ),
        report_style="assessment",
    )
