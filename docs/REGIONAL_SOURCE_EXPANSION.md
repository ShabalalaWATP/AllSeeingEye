# Regional and shared source expansion

Research date: 6 September 2026. Companion to the
[implementation plan](RESEARCH_EXPANSION_IMPLEMENTATION_PLAN.md).
This is a source onboarding backlog, not an enabled-source list. First-party
pages/documentation were reviewed; new feed/API endpoints have not been live
integration-tested and redistribution rights have not been assumed.

## 1. Source classes and onboarding

Use three distinct roles within each regional preset:
1. Original records/statements: what an institution filed, published or stated.
2. Reporting/analysis: claims whose attribution and original sourcing remain visible.
3. Observations/datasets: measurements with temporal/spatial and sampling limits.

An official statement is primary evidence of that statement, not automatic proof
of its underlying claim. An opposition outlet, government outlet or think tank
gets no automatic grade from its political alignment. Existing grades remain
versioned; new/unreviewed origins remain explicitly unassessed.

Status shorthand used below:
- **E**: bounded adapter/seed exists in code; operational health still needs checking.
- **D**: first-party machine-readable interface or download documented; adapter pending.
- **L**: first-party publication available; permitted feed/API access not yet established.
- **I**: candidate for deliberate published-file import/reference after licence review.
- **B**: access check failed; record as unavailable until resolved normally.

`L` and `I` are not permission to scrape. A public web page or interactive map is
not a reusable feed. Never construct production endpoints from a guessed `/feed`
path. Discover from publisher documentation, validate content and record the exact
origin. Public ArcGIS availability does not establish redistribution rights.

For every source record store publisher, origin family, languages, topics, regions,
access class, transport, required account, allowed retention/export, attribution,
expected update cadence, actual last success, coverage dates, geographic precision,
request/byte limits, parser version, review date and assessment rationale.
No fake accuracy percentage or synthetic last-success timestamp.

## 2. Russia preset

Default enquiry languages: Russian and English, with Ukrainian when relevant.
Geography includes cross-border relationships and reporting relevant to the query;
a Russia preset must not discard evidence merely because its source is elsewhere.

| Source | Status / priority | Addition and collection route | Map use and limits |
| --- | --- | --- | --- |
| [Meduza](https://meduza.io/en) | E English; L Russian, first slice | Existing EN feed plus publisher-confirmed RU feed; preserve same publisher family across editions | Reported places only; RU/EN editions are not independent corroboration |
| [Mediazona](https://zona.media/) | L, first slice | Publisher page advertises RSS; validate that linked endpoint and permitted excerpts | Dated reporting with city/admin-area precision, not personal address mapping |
| [The Insider](https://theins.co/en) | L, first slice | Publisher advertises RSS; verify current canonical origin and EN/RU endpoints | Sourced organisation/event links; mirrors and translated editions share origin |
| [IStories](https://istories.media/en/) | L/I, second slice | Investigation references and permitted feed/published document imports | Dated relationships, with source claims distinguished from reviewed identity matches |
| [ISW Russia/Ukraine coverage](https://understandingwar.org/analysis/russia-ukraine/) | L/I, regional layers | Analysis references first; polygons only from documented current releases with confirmed rights | Label assessed control and release date; not sovereign borders or real-time truth |
| [Bellingcat](https://www.bellingcat.com/) | L/I, second slice | Published investigations and specifically reusable supporting datasets | Map only cited geometry supported by the released methodology |
| [Russian government / MFA](https://government.ru/en/department/92/) and existing TASS English | E TASS; L official documents, first slice | Official position/announcement comparison; approved feeds or manual records | Interested-party statements remain attributed; publication location is not incident location |

Existing Ukrainian reporting and international feeds remain available for context
and challenge. Russian public registries are a discovery backlog, not a promised
free API: verify present access/licence before adding any registry adapter.

## 3. China preset

Keep simplified Chinese, traditional Chinese and English distinct. Names may need
original characters, pinyin and established English aliases, without silently
merging organisations. Existing SCMP and Nikkei feeds are reused, not new sources.

| Source | Status / priority | Addition and collection route | Map use and limits |
| --- | --- | --- | --- |
| [China Digital Times](https://chinadigitaltimes.net/) | L, first slice | Publisher documents RSS, but older [subscription guidance](https://chinadigitaltimes.net/chinese/184613.html) is not proof that those endpoints remain current | Censorship/reporting context; no inferred precise location from an online post |
| [MERICS](https://merics.org/en) | L/I, second slice | Public analysis and permitted reports; membership material excluded unless separately authorised | Policy/economic context with dated source references |
| [AidData datasets](https://www.aiddata.org/datasets) and [China dashboard](https://china.aiddata.org/) | D/I, regional layers | Versioned downloadable finance/project records after checking licence and selected release | Overseas project locations and uncertainty; commitments, disbursements and completed projects are different |
| [CSIS ChinaPower Taiwan ADIZ data](https://chinapower.csis.org/data/taiwan-adiz-violations/) | I, regional layers | Inspect current downloadable format, period, methodology and rights | Aggregate reported counts/areas, never invented aircraft tracks; ADIZ is not territorial airspace |
| [CSIS AMTI](https://amti.csis.org/) | L/I, regional layers | Island/geographic references; no presumed vector/image export rights | Separate physical features, claimed areas and dated analytical assessments |
| [PRC Ministry of Foreign Affairs](https://www.fmprc.gov.cn/eng/) | L, first slice | Original briefings and statements through verified permitted interfaces or imports | Official claims compared with other evidence; map relevant places, not all stories at Beijing |
| SCMP and Nikkei Asia, existing code seeds | E, first slice | Reuse current feed access, strengthen query routing and provenance | Excerpt/paywall limits remain; never fabricate full article content |

Further discovery: Taiwan primary public releases, official Chinese statistical
releases and exchange/company filings. Verify machine access and reuse before
promising connectors. ChinaPower and AMTI share CSIS parentage and may cite the
same originating government release; track both relationships explicitly.

## 4. Iran preset

Persian (`fa`) is a required new capability. It is currently absent from the
profile/report language choices. Arabic and English are complementary, not a
replacement for Persian collection. Preserve Persian names and original calendar
information; translated and original editions retain one source family.

| Source | Status / priority | Addition and collection route | Map use and limits |
| --- | --- | --- | --- |
| [IranWire](https://iranwire.com/en/about) | L, first slice | Persian/English reporting through a verified permitted feed or selected published documents | Reported place and source context; protect citizen-source identifying details |
| [Iran International](https://www.iranintl.com/en/abouten) | L, first slice | Persian/English reporting; confirm available machine interface and rights | Record publisher/editorial context and attribution, never a blanket reliability upgrade |
| [HRANA](https://en-hrana.org/) | L/I, first slice | News and published human-rights reports; validate any publisher feed before enabling | Aggregate at supported city/admin area; avoid mapping victims' or witnesses' homes |
| [Iran Human Rights](https://iranhr.net/en/) | L/I, second slice | Dated reports and selected permitted datasets | Reported counts with periods/methodology; different counts may have different coverage |
| [IAEA Iran monitoring](https://www.iaea.org/topics/monitoring-and-verification-in-iran) | L/I, first slice | Selected public reports, resolutions and statements with document/page citations | Regional/contextual views and dated findings; publication is not proof of current inspection coverage |
| [OONI developer documentation](https://docs.ooni.org/) | D, regional layers | Bounded public measurement aggregates for Iran and other countries | Country/ASN/time censorship observations, not precise probe locations or proven causes |
| [IODA HTTP API](https://api.ioda.inetintel.cc.gatech.edu/v2/) | D, regional layers | Connectivity/outage aggregates after current terms/rate-limit verification | Show signal and time interval; outage observation is not proof of a government order |
| [Iran MFA](https://www.mfa.gov.ir/en) / IRNA discovery | B MFA; L discovery | MFA browsing check failed; discover normal permitted primary-statement access, otherwise manual records | Label unavailable, no circumvention or inference that silence confirms another source |

The first Iran release must disclose which of these sources are actually
operational. Do not label the preset comprehensive merely because eight names
appear in the catalogue.

## 5. Shared sources for all three and wider-topic research

| Source | Route/status | Value and boundary |
| --- | --- | --- |
| [UK Sanctions List](https://www.gov.uk/government/publications/the-uk-sanctions-list) | D, primary published files | Designation identifiers/aliases and dates. Use current UK list, not retired OFSI exports |
| [OFAC Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service) | D, structured files | Designations and changes; possible identity matches remain separate from confirmed matches |
| [ITA screening API](https://developer.trade.gov/) | D, optional account/key | Export-screening list records; list type, underlying issuing authority and current portal requirements survive ingestion |
| [GLEIF Level 2](https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom) | E, exact profile/direct/ultimate parent adapters | Frozen report relationship view added; LEIs and reported accounting parents, not a complete beneficial-ownership register |
| [Companies House API](https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/persons-with-significant-control/list-statements) | E profile, D extension | Officers/control/selected filings with optional existing key; submitted assertions remain attributed |
| [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | E metadata, extension pending | Selected filings and financial facts, keeping accession IDs and original documents |
| [Contracts Finder](https://www.contractsfinder.service.gov.uk/apidocumentation) / [Find a Tender](https://www.gov.uk/government/publications/open-contracting) | D | Dated procurement links; tenders/awards are not actual payments, supplier address is not project site |
| [Copernicus STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) | D, catalogue then imagery | Capture-date and cloud/resolution-aware imagery discovery; download/processing quotas checked separately |
| [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/) | Optional bounded NOAA-20 live adapter implemented; key onboarding/live acceptance pending | Server key, UTC acquisition time and sensor quality; see [operations](FIRMS_OPERATIONS.md). Detections do not establish attacks or explosions |
| [OpenAlex](https://help.openalex.org/api/) / [Crossref retractions](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/) | D | Research literature and publication status; metadata not guaranteed full text or scientific validity |
| [World Bank indicators](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures) | D | Dated macro context; units, coverage, reporting lag and revisions visible |
| [UK Parliament APIs](https://developer.parliament.uk/) | D | Primary statements/questions/answers; source of what was said, not automatic factual endorsement |
| [CourtListener](https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47) | D, access tier review | Available US opinions/dockets; allegations, decisions and findings distinguished |
| [Common Crawl index](https://commoncrawl.org/cdxj-index) | D, historical discovery | Incomplete historical captures; index match does not mean the needed passage was preserved |

Optional later: [OpenSanctions](https://www.opensanctions.org/docs/bulk/) for joined
entity records, subject to its API/data licensing. No paid integration is assumed.
FIRMS currently marks its country-list/country endpoints unavailable. Plan around
the documented area/date/sensor endpoint and explicit availability checks.
Reuse existing maritime, aviation, disaster and GNSS adapters where available;
measure source coverage before adding redundant trackers. Global Fishing Watch
and other specialist feeds remain separate access/licence feasibility work.

## 6. Implement one adapter completely before expanding the list

1. Record discovery reference, exact approved endpoint, provenance and usage terms.
2. Confirm HTTPS, redirect/origin behaviour, parser content type, schema, pagination,
   time precision, languages, refresh cadence, update/removal semantics and limits.
3. Add immutable offline fixtures for good/empty/error/malformed/stale/duplicate
   results and distinguish blocked, unavailable and unsupported.
4. Implement through the existing guarded HTTP port with source-origin credentials,
   bounded request/response sizes, caching/backoff and request budget accounting.
5. Normalise source content without losing original language, record ID, attribution,
   publication/event/capture time or permitted exact citation locator.
6. Do not geoparse publisher addresses as event coordinates. Produce geometry only
   when the evidence supports it; unlocated findings are first-class results.
7. Wire source catalogue, regional presets, reports, map eligibility and admin tests.
8. Test cross-scope isolation, shared-origin deduplication, source corrections,
   failure disclosure, source text injection and language/date edge cases.
9. Run a normal live smoke test when access is configured, record the date and
   result, then mark operational. A successful fixture test means implemented only.

Initial onboarding order: existing regional seeds and verified publisher RSS;
primary UK/OFAC records and GLEIF; Companies House/procurement; OONI/IODA; approved
AidData/ChinaPower layers; Copernicus/FIRMS; permission-dependent analysis maps;
then literature/history/court breadth. Documentation-only sources remain usable
as references or deliberate supported imports without pretending automated coverage.

## 7. Source acceptance scenarios

- A Russian original and its English translation count as one reporting origin.
- Two outlets quoting the same official statement do not create three observations.
- A Chinese company's English trading name does not merge different legal entities.
- A Persian location/date can retain ambiguous transliteration/calendar interpretation.
- A sanctions name match returns candidates and reasons, not an automatic accusation.
- A disconnected Iran source returns an unavailable receipt, never an empty-success
  result labelled as evidence of no events.
- A source's correction updates future analysis while preserving older frozen reports.
- A permissions-restricted map remains a link and cannot be exported as copied data.
- A thermal or connectivity anomaly is not assigned a cause without separate evidence.
