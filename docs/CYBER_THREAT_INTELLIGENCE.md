# Cyber threat intelligence workspace

Implemented 12 September 2026. Open **Cyber intelligence** in the main navigation
(`/cyber`). This workspace combines public reporting, historical actor reference
and a personal cited briefing. It does not claim to measure all cyberattacks.

## Operator workflow

Choose 2, 5, 7 or 14 days. The exact start and end dates are displayed separately
from the briefing's 24-hour refresh interval. The overview summarises collected
record types, daily publication volume, actor-name mentions and source-supplied
country context. A missing observation is never a measured zero threat level.

- **Activity:** search returned titles, source names, CVEs and products; narrow by
  evidence type, country context or matched actor. Each entry has its source,
  publication date, grade and a link to start deeper research.
- **Threat actors:** search 176 MITRE Enterprise ATT&CK profiles by name,
  associated name, identifier or description. Inspect historical descriptions,
  technique links, reference dates and current name matches. Associated names
  can overlap only partly; a mention is not verified incident attribution.
- **Exploited vulnerabilities:** view CISA KEV additions, affected products,
  reported ransomware use and required action. The catalogue addition date is
  not the start of exploitation. Federal directive deadlines are labelled with
  their scope rather than presented as universal deadlines.
- **Intelligence briefing:** an executive overview, developments, defensive
  implications, watch conditions and references, using the existing professional
  report reader. Open the saved report for Word, PDF or Markdown export.

The personal Deep briefing uses the normal research pipeline and configured AI
connection. Its admission identity is per owner and reporting window, with reuse
for 24 hours. Country, actor and keyword display filters do not admit another job
or silently change the worldwide briefing. Progress, errors and incomplete
reports remain visible. No real-model quality evaluation was performed for this
milestone; fixture rendering and workflow tests do not establish analytical accuracy.

## Sources and current coverage

Seven public publisher feeds were added without new credentials. Probes on
12 September returned usable XML from all seven; publication freshness differs.

| Publisher | Content | Source |
| --- | --- | --- |
| UK NCSC | Threat reports and separate news/threat statements | [Official RSS directory](https://www.ncsc.gov.uk/information/rss-feeds) |
| Microsoft | Threat Intelligence reporting | [Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/) |
| Cisco Talos | Threat research | [Talos Intelligence](https://blog.talosintelligence.com/) |
| Google / Mandiant | Threat research | [Google Threat Intelligence](https://cloud.google.com/blog/topics/threat-intelligence) |
| CERT-EU | Threat intelligence publications | [CERT-EU publications](https://cert.europa.eu/publications/threat-intelligence) |
| Australia ACSC | Official advisories | [ACSC advisories](https://www.cyber.gov.au/about-us/view-all-content/advisories) |

Publisher collection retains headlines, dates, attribution and links, not full
articles. These new sources start with explicit unassessed F6 grades. Publisher
authority is not automatically a credibility score. NCSC's two feeds share one
organisation for independence assessment. Feed-supplied publisher geography is
discarded. CERT-EU CET/CEST dates use a source-specific fixed-offset normalisation
with the original date and method retained as provenance.

The working existing API connectors are included:

| Source | Meaning | Probe result on 12 September |
| --- | --- | --- |
| [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Recorded exploitation, bounded recent catalogue additions | 44 recent entries |
| [Ransomware.live](https://www.ransomware.live/) | Publicly relayed criminal victim claims, not independently verified breaches | 100 claims |
| [IODA](https://ioda.inetintel.cc.gatech.edu/) | Country connectivity signals, not proof of malicious cause or a continuing outage | 146 warning/critical records |

These are one-time delivery observations, not availability guarantees. CISA RSS
requests returned 403 and were not activated as empty feeds; KEV remains separate.
The NCSC threat-report feed was reachable but its newest item was dated 7 May
2025. It may therefore contribute no records to a recent period. The source
coverage disclosure shows delivery status and last successful collection; delivery
health alone does not establish fresh publication or editorial reliability.

The actor reference is a packaged, licensed projection of MITRE Enterprise ATT&CK
v19.2, with 176 non-revoked/non-deprecated groups and 4,628 direct technique
associations. No runtime external request is needed. The pinned commit, checksum,
licence and offline update instructions are in the
[reference provenance](../backend/src/ase/adapters/cyber_reference/README.md).
Administrative source controls can disable both reference release and derived
name matches. Profiles are historical, not a current activity or sponsorship list.

## Map and globe

The dedicated **Cyber** shield switch and adjacent filter control live on the
left layer rail. It is off by default, preserving the existing conflicts-only
default. Cyber no longer has a duplicated toggle under Topics & time.

Type and keyword filters work in both projections. Enabling **Cyber** now also
shows source-attributed ransomware victim and outage country references. **Show
approximate country context** starts selected and can be cleared independently;
that choice survives switching the layer off and on within the session. These
labelled count markers use country centres as reference
locations. They are not incident coordinates, attacker origins or attack paths.
Advisories and KEV records do not acquire locations from publisher headquarters.

Selecting a reference marker opens its source records and highlights the selected
context; closing the inspector clears it. Genuinely located events retain the
existing geographic precision checks and receive a shield symbol. Country-only
records remain in the Not plotted precision group, even when reference markers
are displayed. Shared country, time and location-quality controls still apply.

**Open cyber map** deliberately enables Cyber and its labelled country context,
carrying the selected period, country, type and search. It preserves other layer
choices. It does not manufacture a point for the selected report.

The map snapshot refreshes 60 seconds after each completed request while Cyber
is enabled and the page is visible. Requests do not overlap; hiding the page,
disabling Cyber or changing account/access cancels pending work. An initially
empty snapshot can therefore populate after the feed workers warm up. The
filter panel distinguishes collected records, country references and located
records, and explains when the selected records cannot be placed on the map.

The IODA poll now requests the latest hour every 15 minutes, still capped at
300 input rows. A 13 September public probe found the previous 24-hour request
filled its limit with early records and missed recent alerts available in a
one-hour request. Overlapping polls build the existing retained history; startup
does not backfill a complete day. Busy hours can still hit the cap and this is
not complete outage coverage. See the [IODA API](https://api.ioda.inetintel.cc.gatech.edu/v2/).

## Bounds and security

- Fourteen-day cyber retention uses the existing 5,000-category item cap and
  global memory budget. It does not recover missing publisher archives or survive
  process restart. Only selected frozen report evidence is persisted.
- Page counts cover the admitted dated selection. The newest 200 records are
  returned for browsing, with 30 initially rendered. Actor lists render 24 at a
  time. The separate map context snapshot is bounded to 500 records and 25 list
  entries, independent of viewport streaming.
- Snapshot preparation runs in a bounded thread outside the event loop and
  shared source-control guard. Source controls and current session access are
  checked again before release. A 5,000-record synthetic benchmark measured
  2.492 seconds preparation and 0.004 seconds guarded release on the development
  host; this is not a production latency guarantee.
- Read-only snapshot requests retry a busy response at most four times, honouring
  short server cooldowns. Changing period, access or identity cancels the old
  request and retry timer. Longer cooldowns remain explicit errors with manual
  retry. Briefing creation is not automatically replayed by this retry policy.
- Only known publication dates inside the selected half-open period contribute
  to snapshot counts. Daily chart endpoints may represent partial calendar days;
  multiple IODA sensor records are not distinct attacks.
- Source text remains bounded plain text. Links use existing safe-link rendering;
  no source HTML, criminal leak links, malware downloads or active scanning is
  introduced. The existing guarded network client handles collection.
- Reports use existing owner/session authorisation and citation validation.
  Access changes hide old client data and cancel outstanding scoped work.
- No new runtime dependency, API key, migration or production infrastructure is
  required. Broader archive depth, source diversity and real-model quality remain
  evaluation work rather than assumed coverage.

The APIs are `GET /api/cyber?days=2`, `GET /api/cyber/actors` and
`POST /api/cyber/briefing?days=2`. Supported periods are 2, 5, 7 and 14. These are
authenticated APIs; generated OpenAPI types are the frontend contract.
