# Cyber threat intelligence workspace

Implemented 12 September 2026 and rebuilt as a single scrolling CTI page on
13 September 2026. Open **Cyber intelligence** in the main navigation (`/cyber`).
The workspace combines public reporting, historical actor reference, themed
lenses, the aircraft-derived GNSS interference proxy and a personal cited
briefing. It does not claim to measure all cyberattacks.

## Page structure

Nothing is hidden behind tabs. A sticky section bar jumps between:

| Section | Content |
| --- | --- |
| Overview | Six stat tiles with daily sparklines, a stacked daily volume chart by record kind (with legend and table view), share by kind, countries in the evidence, NATO member context and source output. |
| Live board | Fixed-window counts from the live event feed, independent of the chosen period: outage alerts in the last 24 hours by nation, and ransomware claims in the last 7 days by group and by claimed victim nation. This replaces the former `/trackers/cyber` board, which now redirects here with its query string. |
| Assessment | The executive paragraph and key points of the AI briefing for the period, with progress, pause and error states, plus a short reading guide. |
| Focus areas | Six lens cards: nation-state activity, NATO members and allies, UK critical national infrastructure, Ukraine, GNSS interference and navigation warfare, critical infrastructure and OT. Each shows its count and trend, the briefing's own passage under that heading when one exists, the latest matched records and a filter action. |
| Nation-state | Records per state named in mentioned actors' MITRE profiles, and the actors mentioned with their profile association. |
| GNSS | Amber and red aircraft-accuracy cells grouped into named regions, the worst cells, the latest observation time, a map hand-off that enables the GNSS layer, and reporting that mentions jamming or spoofing. |
| Vulnerabilities | CISA KEV additions with required action, ransomware-use flag and scoped due dates. |
| Actors | The MITRE ATT&CK reference with search, inspector, technique links and the profile's state association. |
| Activity | Every returned record with source, grade, lenses and matched names; filters for keyword, evidence type, country context, lens and actor. |
| Briefing | The complete cited report in the professional reader. |
| Sources | Delivery health, retained counts and the coverage note. |

Periods are 2, 5, 7, 14 or 30 days and are carried in the URL. The cyber retention
budget is 30 days and 8,000 records so the longest period can be served from the
bounded in-memory store; publisher archives are still not recovered on restart.

## Lenses

A lens is a deterministic keyword and metadata match over the bounded headline
text of each record (`ase/domain/cyber_themes.py`). It says the record mentions a
topic. It never establishes who acted, whether an incident occurred, or that an
unmatched record is unrelated. The rules are:

- **Nation-state:** state-sponsorship and espionage vocabulary, state-service
  acronyms, numbered APT/UNC designators, vendor naming families, or a mention of
  a group whose reference profile records a state association.
- **NATO members and allies:** alliance, allied-government and defence terms, or a
  member state named together with incident language. A ransomware claim against a
  firm in a member state is not automatically alliance activity.
- **UK critical national infrastructure:** UK context (UK terms, a GB country code
  or an NCSC publication) combined with infrastructure or sector terms, or a GB
  connectivity signal.
- **Ukraine:** CERT-UA publications, UA-attributed records, Ukrainian places and
  organisations, and tracked UAC clusters.
- **GNSS interference:** GNSS, GPS and constellation names, jamming, or spoofing in
  a navigation context. E-mail spoofing does not match.
- **Critical infrastructure and OT:** industrial control, energy, water, transport,
  health and telecommunications terms, including ICS vendor names that appear in
  CISA advisories.

Snapshots return each record's lenses, a per-lens count with a daily series, and
records-per-state tallies.

## State associations

The packaged MITRE ATT&CK projection is unchanged. At load time the catalogue
derives `state_association` from each profile's own wording
(`assessed_state_association` in `ase/domain/cyber_actors.py`): explicit cues such
as "attributed to", "sponsored by", "operating out of", nationality-plus-role
phrases such as "Chinese state-sponsored" or "North Korea-aligned", and named
organs such as GRU or IRGC. Hedged sentences ("circumstantial", "may be",
"reportedly", "allegedly", "similarities to", "no confirmed link") and phrases
that describe targets are ignored. On the packaged v19.2 release this yields
associations for 94 of 176 groups; the remainder are financially motivated,
unattributed, hedged or described only by language. The UI always labels the
value as the profile's wording, not an attribution of any new report. Review the
derived values whenever the packaged release is updated, because MITRE wording
changes over time.

## Sources and current coverage

Sixteen public publisher feeds are registered without new credentials. The nine
added on 13 September were probed with the application's own user agent and
returned XML with dated items:

| Publisher | Content | Language | Feed |
| --- | --- | --- | --- |
| UK NCSC | Threat reports; news and threat statements | en | ncsc.gov.uk RSS |
| Microsoft | Threat Intelligence reporting | en | Security blog feed |
| Cisco Talos | Threat research | en | blog.talosintelligence.com |
| Google / Mandiant | Threat research | en | Threat Intelligence feed |
| CERT-EU | Threat intelligence publications | en | cert.europa.eu |
| Australia ACSC | Official advisories | en | cyber.gov.au |
| US CISA | Cybersecurity and ICS advisories, KEV notices | en | cisa.gov/cybersecurity-advisories/all.xml |
| CERT-UA | Incident and threat reports | uk | cert.gov.ua/api/articles/rss |
| Canadian Centre for Cyber Security | Alerts and advisories | en | cyber.gc.ca RSS API |
| CERT-FR (ANSSI) | Alerts and advisories | fr | cert.ssi.gouv.fr/feed |
| FBI IC3 | Public service announcements | en | ic3.gov/PSA/RSS |
| SANS Internet Storm Center | Handler diaries | en | isc.sans.edu/rssfeed.xml |
| Palo Alto Unit 42 | Threat research | en | unit42.paloaltonetworks.com/feed |
| The Record | Specialist cyber news | en | therecord.media/feed |
| BleepingComputer | Specialist cyber news | en | bleepingcomputer.com/feed |

The two news outlets use the new `news_report` record kind so journalism is never
counted as vendor or official research. All publisher records start with explicit
unassessed F6 grades and keep headlines, dates, attribution and links only.
CERT-UA and CERT-FR items are retained in their own language for the workspace;
the English-language briefing request names only English publishers because
private collection follows the owner's research languages. ENISA news,
WeLiveSecurity, CCDCOE, SSSCIP, NCSC Ireland and Google TAG answered 403 or 404
and were not added. IC3 writes RFC 822 dates with a colon in the numeric offset;
the shared date resolver now removes that colon before parsing without changing the
declared zone.

The existing API connectors remain: CISA KEV (recorded exploitation), Ransomware.live
(unverified criminal claims) and IODA (connectivity signals, not attacks). The
GNSS section reads the aviation tracker's jamming map, an ADS-B accuracy proxy for
roughly the last 24 hours; see `GNSS_AND_MAP_CONTROLS.md` for what the cells can
and cannot say. Region boxes are reading aids, not attribution.

## AI briefing

The personal briefing uses the normal research pipeline and configured AI
connection, one job per owner and period, reused for 24 hours. Its prompt now asks
for explicit headings for nation-state activity, activity against NATO members and
allied governments, UK critical national infrastructure, Ukraine, and GNSS
interference and navigation warfare, and instructs the model to say when a heading
has no evidence rather than infer activity. At most twelve upstream search terms
are allowed, so the term list balances broad recall with the themed topics. The
page reads themed passages back out of the saved report by heading; when a heading
is absent the card says so. No real-model quality evaluation was performed for this
milestone.

## Map and globe

The Cyber layer, country references and **Open cyber map** behave as before. The
GNSS section's **Show GNSS cells on the map** enables the interference layer before
navigating. The former event-scope strip at the top of the map was removed on
13 September; the same refinements remain in their panels.

## Bounds and security

- Lens matching runs in the same bounded worker as name matching; text is capped at
  3,000 characters per record and profiles at 800 characters.
- Snapshot responses remain bounded: 200 returned records, 31 timeline days, six
  lens tallies, at most 20 state tallies with 12 group identifiers each.
- Source controls still govern release: disabling the MITRE reference removes name
  matches, the derived nation-state lens and state tallies in the same response.
- No new runtime dependency, API key, migration or production infrastructure is
  required. Feeds were verified once on 13 September; delivery health alone does not
  establish fresh publication or editorial reliability.

The APIs are `GET /api/cyber?days=2`, `GET /api/cyber/actors` and
`POST /api/cyber/briefing?days=2`. Supported periods are 2, 5, 7, 14 and 30.
These are authenticated APIs; generated OpenAPI types are the frontend contract.
