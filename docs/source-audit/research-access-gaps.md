# Research source access and coverage audit

Reviewed 10 September 2026 against the code at the start of the source audit
(baseline `4528ca6`) and the primary documentation linked below. This document
covers question-led research, news, conflicts, country coverage, public records,
humanitarian context and cyber observations. Other audit documents cover live
aviation, maritime, space, imagery and camera providers.

**The main shortfall is usable collection coverage, not the number of names in
the catalogue.** Several good sources already have adapters but require access
or a dataset import. Others work on the live dashboard but are not available to
question-led research. Precise area research initially has a retained-feed search
and a restricted Copernicus scene query, not a fresh search of every provider.

## 1. What is actually implemented

The source-of-truth composition is `backend/src/ase/container/research.py` for
research and `backend/src/ase/adapters/feeds/registry.py` for live collection.
`research_sources.py` describes capabilities; registration does not establish
credentials, successful collection, geographic eligibility or completeness.

| Family | Baseline implementation | Consequence for use |
| --- | --- | --- |
| Google News | One question-specific RSS request per selected supported edition, within the shared budget; first 200 items, local exact publication-window filtering | Broad discovery but an undocumented RSS interface. Private phrases go to Google. No article bodies; edition choice does not verify article language or incident geography |
| Publisher feeds | 38 live RSS/Atom seeds: 7 official/context, 14 news outlets, 9 social feeds and 8 regional feeds | The baseline research factory only registers the 8 regional and 9 social seed families, not the 21 official/general news seeds. Reusing these 21 is a high-value integration gap |
| Native-language feeds | 32 English, 3 Russian, 1 Chinese and 2 Persian seeds | Many English sources and translated search editions are not native-language diversity. Arabic, Ukrainian, traditional Chinese, African and Latin American direct feeds are notably thin |
| Regional research | Meduza RU, Mediazona RU, The Insider RU, China Digital Times ZH, HRANA FA/EN and IranWire FA/EN | Recent headline matching, not complete archives. Requires matching language and applicable region or explicit selection |
| Social | Six outlet YouTube channel feeds, three Reddit community feeds and configured Mastodon watchlists in live collection; question research over the nine RSS feeds | No platform-wide search, replies or video analysis through those feeds. Posts usually have no reliable geography. A channel is not an independent origin from its publisher |
| Conflict | GDELT machine-coded reports, UCDP Candidate release, optional ACLED; ReliefWeb for humanitarian context | Distinguish coded incident, provisional historical baseline, unrest and contextual news. An LLM can screen relevance but cannot turn a weakly located headline into an independently verified event |
| Company | SEC directory/submissions and selected filing workflow; Companies House profile/officers/PSC; GLEIF exact LEI/profile/accounting parents | Strong starting points. Bounded records and exact identifiers, not complete corporate ownership or global company search |
| Sanctions | UKSL and OFAC SDN imported snapshot providers | No upstream key is needed. A validated local snapshot and a refresh workflow are needed. No list means no coverage; a name match remains a candidate |
| Procurement | One bounded Contracts Finder publication page matched locally | Searching 20 recent notices cannot establish a company's full procurement history. Broader UK/EU/worldwide procurement remains a gap |
| Development | Local AidData GeoGCDF catalogue; World Bank explicit country/annual indicator | Imports/explicit indicators, with dates and units. Not a general live search of Chinese overseas projects |
| Domain | RDAP, DNS and optional SSLMate certificate-transparency search | Passive public context only. CT requires a key and is a bounded current first page, not proof of service ownership or complete history |
| Literature/politics | OpenAlex and Crossref metadata; UK Parliament written questions | Useful topic breadth, explicit selection/subject routing. Metadata is not paper full text or a scientific reliability verdict |
| Cyber/connectivity | CISA KEV, ransomware.live and IODA live feeds; opt-in OONI country/day research aggregates | Live-source presence does not imply all three can be queried for a private question or exact map polygon |
| Area | Retained public events, restricted Copernicus footprints; AidData only under its historical recorded-time mode | Existing display switches do not govern research. CCTV/infrastructure directories are not searched by the retained-event provider |

The feed counts above were calculated by importing the four seed collections,
not by counting catalogue rows. The local code was inspected; this audit did not
probe every individual publisher feed again. The previous actual publisher
transport results are in [the dated feasibility record](../SOURCE_FEASIBILITY_2026_09.md).

## 2. Current access requirements, distinct from code gaps

The main audit checked local settings without exposing values. At the start of
this work, Companies House, SSLMate CT Search, UCDP, ACLED and ReliefWeb were all
unconfigured. UKSL, OFAC and AidData had neither configured paths nor files.
OONI acknowledgement was false. A genuine feed contact was configured. FIRMS
and AISStream keys were present, but presence alone does not establish successful
collection. No secret values were read or copied by this research subtask.

| Existing integration | Required setting/action | Access contract and practical decision |
| --- | --- | --- |
| Companies House profile/officers/PSC | `ASE_COMPANIES_HOUSE_KEY` | Create a developer application and an API-key client, not a stream/OAuth client. Existing code is ready to use it. Public API allowance: 600 requests/5 minutes; app already paces requests. [Create application](https://developer.company-information.service.gov.uk/how-to-create-an-application), [rate limits](https://developer-specs.company-information.service.gov.uk/guides/rateLimiting) |
| SSLMate CT Search | `ASE_CERTIFICATE_TRANSPARENCY_KEY` | Choose Certificate Search API Small, $0/month. It allows 100 single-hostname queries/hour, 75/minute, 5/second and 15-second queries, reducible during load. Existing code uses exact hostnames. This is distinct from paid Cert Spotter monitoring. [Correct product](https://sslmate.com/pricing/ct_search_api), [API](https://sslmate.com/help/reference/ct_search_api_v1) |
| UCDP API | `ASE_UCDP_ACCESS_TOKEN` | Free token requested from the maintainer with real name, affiliation (including independent) and intended use. Typical stated review is 3–5 working days. Existing public Candidate CSV fallback means this is an efficiency/history-query improvement, not an emergency fix for all conflict coverage. [Official token request and API](https://ucdp.uu.se/apidocs/) |
| ACLED events | `ASE_ACLED_ACCESS_TOKEN` plus event-data entitlement | The app accepts an externally supplied OAuth token and does not renew it automatically. A personal Gmail address receives Open myACLED aggregated access. That does not unlock the current event adapter. Do not claim institutional affiliation or promise a free event-level feed. [Access tiers](https://acleddata.com/myacled-faqs) |
| ReliefWeb reports | `ASE_RELIEFWEB_APPNAME` | Free read API V2 needs an approved appname. Submit the appname request form linked in the official parameters page. It is not the separately restricted Publishing API. Current quota: 1,000 calls/day and 1,000 results/call. Existing live adapter is V2 and returns up to 100 metadata records. [Appname approval](https://apidoc.reliefweb.int/parameters#appname), [read API](https://apidoc.reliefweb.int/) |
| SEC | Real `ASE_FEEDS_CONTACT` | No API key for public submissions or XBRL APIs. Existing client rejects placeholder contacts and uses guarded server-side access. Do not create a filer account to read public data. [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) |
| OONI | `ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED` | No key. This is a use-rights decision, not missing authentication. Data are CC BY-NC-SA 4.0; code defaults unavailable until appropriate use is acknowledged. Country/day counters, maximum 14 days, no probe-level collection. [API](https://api.ooni.io/), [data licence](https://github.com/ooni/license/blob/master/data/LICENSE.md) |
| UK sanctions | Validated `ASE_UKSL_SNAPSHOT_PATH` | No key. Import current UKSL with authority/version/hash/licence. The OFSI list stopped updating on 28 January 2026. [Current formats](https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list), [transition](https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026) |
| OFAC SDN | Validated `ASE_OFAC_SDN_SNAPSHOT_PATH` | No key for public exports. Existing snapshot adapter needs an imported, dated record, not arbitrary JSON or a guessed timestamp. Keep original authority identifiers and delisting freshness visible |
| AidData | Validated `ASE_AIDDATA_CATALOGUE_PATH` | Dataset download/import and chosen release rights, not an API key. Label commitment year, geometry uncertainty, dataset coverage and publication date separately |
| OpenAlex | No credential support in baseline | Basic calls remain keyless under current official documentation. A free account key raises daily allowance 10×, but needs explicit server-side wiring. Use bearer header rather than query-string secrets. [Authentication](https://help.openalex.org/api/authentication/), [free account pricing](https://help.openalex.org/access/buying-and-renewing/) |
| Copernicus metadata | None for implemented catalogue query | The existing adapter queries scene metadata. Do not equate free catalogue access with unlimited imagery download, processing, useful cloud-free coverage or change detection |

Recommended immediate account order: Companies House, SSLMate CT Search,
ReliefWeb appname request, UCDP token request, then OpenAlex if scholarly usage
justifies credential wiring. ACLED is worth an honest eligibility check, but a
generic-email account cannot close the mapped unrest/event gap by itself.

The main audit reported a browser-control startup failure, so no completed signup
or new linkage is implied by these recommendations. A linked Gmail account was
available for the authorised onboarding workflow; that does not itself grant any
provider entitlement. Check the main audit's final results for later changes.

## 3. Five practical collection improvements

These are ranked by useful new evidence and implementation feasibility, not by
marketing claims or nominal source count. They are proposed work at the audit
baseline; check the main audit's implementation results before treating any as
delivered.

| Rank | Improvement | Admission and evidence contract | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | Fresh USGS FDSN area research, no key | Explicit UTC dates plus area envelope; enforce exact polygon membership locally. Preserve earthquake occurrence, last revision, magnitude, depth and upstream ID. Do not use keyword matching to discard a quake from a neutral area overview | One bounded request; explicit row limit/truncation; dateline and empty/error fixtures; no false claim that the whole USGS catalogue was searched |
| 2 | Fresh NASA EONET area research, no key | `status=all`, date bounds and documented bbox; filter each dated geometry against the actual drawn shape. Preserve the contributing source, category and track time. EONET is curated context and can overlap FIRMS or other hazard origins | Correct bbox order west,north,east,south; open and closed events; event with multiple dated positions; source deduplication; unknown locations excluded |
| 3 | Reuse official/general publisher feeds in private topic research, no new key | Add the already-maintained 21 seeds with bounded local phrase/date matching, original publisher identity and source controls. They are topic/country context, not automatically exact-area evidence | The planner can select eligible sources; disabled parents disable derivatives; no private phrases sent to publisher feeds; publisher independence preserved; previous budget unchanged |
| 4 | Fresh FIRMS area/date research using existing configured key | Query documented sensor/area/date API only. Keep acquisition time, sensor, confidence and FRP; local exact-area filtering; consolidate coincident detections without declaring explosions or strikes | Multi-sensor request accounting, transaction budget, scan/byte cap, stale/low-confidence disclosure, no credential in URLs/logs returned to users |
| 5 | Dated UCDP area query once API token is available | Use documented version/geography/date filters, retain location/date precision and dataset lag. Filter exact polygon locally. Keep provisional and annual releases distinct | Token origin restriction, bounded pages, truncated receipt, exact temporal interpretation (`date_end` filter), no conversion of city-level accuracy into an exact incident pin |

USGS documents rectangle/radius/date filters and a 20,000-result service ceiling;
our own limits should be much smaller. Its guidance prefers realtime summary
feeds for dashboard polling, with FDSN for bounded research.
[USGS FDSN contract](https://earthquake.usgs.gov/fdsnws/event/1/swagger.json).

EONET supports inclusive date filters, a result limit and bbox filters over event
datapoints. Event closure is a catalogue attribute, not necessarily the exact
physical end of the hazard. Keep locally enforced half-open UTC dates consistent
with the report contract. [EONET V3](https://eonet.gsfc.nasa.gov/docs/v3).

FIRMS and UCDP already have live parsers, but private bounded collection needs its
own provider admission, receipts and budgets. Do not call a live global worker
from a research request or imply that a cached snapshot is newly collected.

### Exact existing publisher roster to reuse

These are existing subscriptions, not new signups. Each should receive a stable
`research_publisher_<parent_id>` identity, a headline-only research view, original
publisher family, the parent's disabling rules and normal collection receipts.
Do not silently fetch article bodies when adapting the live seed's RSS options.

| Group | Existing parent source IDs |
| --- | --- |
| Official/context | `gov_uk_fcdo_news`, `gov_uk_travel_advice`, `us_state_travel_advisories`, `un_news`, `un_press`, `reliefweb_updates`, `crisis_group` |
| International outlets | `bbc_world`, `dw_world`, `france24_en`, `aljazeera_en`, `guardian_world`, `lemonde_en` |
| Regional English outlets | `scmp_news`, `nikkei_asia`, `times_of_israel`, `anadolu_en`, `dawn`, `meduza_en`, `pravda_ua_en`, `tass_en` |

All 21 seeds are configured as English. Preserve TASS's state-controlled context;
do not upgrade reliability when an official feed or outlet becomes selectable.
International Crisis Group is analytical context, not a government issuer. UN
News and UN Press may report the same UN statement. ReliefWeb reports retain the
original contributing organisation and country-level scope. General topic
research should use these feeds before inventing a new web-scraping subsystem.

## 4. Additional sources worth integrating

| Candidate | Value | Access and delivery decision |
| --- | --- | --- |
| ReliefWeb question search | Curated humanitarian reports from many original organisations, disasters, displacement and response context | After appname approval, add bounded keyword/country/date research. Country tagging is broader context, not proof of presence inside an arbitrary small polygon. Preserve contributor rights and family identities |
| HDX HAPI | Administrative-level humanitarian needs, food security, displacement, operational presence and conflict aggregates | App identifier is generated from application name/email; no institution-approval claim. It is not an entitlement bypass for ACLED disaggregated events. Preserve resource metadata and actual coverage. [Getting started](https://hdx-hapi.readthedocs.io/en/latest/getting-started/) |
| IOM DTM V3 | Non-sensitive displacement figures at country, ADM1 and ADM2 level | Developer portal account and subscription key; new adapter required. Versions 1/2 are no longer maintained. Preserve assessment-round dates and administrative aggregation, not invented individual locations. [Official V3 onboarding](https://dtm.iom.int/data-and-analysis/dtm-api) |
| GDELT GEO/DOC | Wide geographic news discovery and a useful cross-check on Google RSS dependence | No account needed for the public interface. GEO maps location mentions near terms; `near` is a bbox search despite its radius syntax. Its output can include HTML popups. Parse into safe structured metadata, never render upstream HTML or promote all matches to conflicts. Current host response/quotas must pass a normal smoke test. [GEO documentation](https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/), [dataset terms](https://gdeltproject.org/about.html) |
| GLEIF name/identifier discovery | Helps users find the exact LEI needed by the existing profile/parent adapters | No need to buy another global registry first. Official API supports name, field and identifier searches; present ambiguous candidates for confirmation. Accounting parentage is not the complete beneficial-owner graph. [GLEIF API](https://www.gleif.org/en/lei-data/gleif-api) |
| ITA Consolidated Screening List | Export-control lists in addition to UK/OFAC designations | Free developer account/subscription key; new adapter required. Preserve original Commerce/State/Treasury list identity, since ITA is an aggregator. Check actual subscribed quota, not a guessed global limit. [Portal onboarding](https://developer.trade.gov/), [API catalogue](https://developer.trade.gov/apis) |
| Cloudflare Radar | Country/ASN outage and traffic anomalies to compare with IODA and OONI | New adapter required. Free account with least-privilege Account → Radar → Read token. It samples Cloudflare-observed traffic, not all Internet users. Reuse/licence approval remains separate. [First request](https://developers.cloudflare.com/radar/get-started/first-request/) |
| IAEA NEWS | Country-reported INES nuclear/radiological events, useful beside the infrastructure inventory | A public RSS link is advertised. Discover the exact link and confirm parse/reuse before adding it. NUCLEUS signup is for optional email notifications, not established as a feed requirement. This is explicitly not an emergency warning channel. [NEWS](https://www-news.iaea.org/Default.aspx), [scope](https://www-news.iaea.org/AboutNews.aspx) |
| OpenSanctions | Joined sanctions/PEP and corporate context | Non-commercial bulk data needs no key; commercial use needs a licence. Free hosted API grants target verified public-interest roles and do not cover generic hobby projects. Do not apply with an invented role. Existing primary UK/OFAC import support is the first win. [Eligibility](https://www.opensanctions.org/docs/commercial/exemption/), [bulk refresh](https://www.opensanctions.org/docs/bulk/updates/) |
| Bluesky public search | Additional public social discovery | Official public AppView exists, but earlier normal host probes returned 403. Re-test once normally before implementing. Do not use alternate hosts or accounts to bypass an explicit block. No reliable incident coordinates should be inferred from profile locations. [Official routing](https://docs.bsky.app/docs/api/app-bsky-feed-get-feed) |

The HDX documentation page was accessible through search, but `hapi.humdata.org`
documentation and the HDX landing page returned 403 through this research tool.
That is a documentation-access observation, not a live application API result.
No new HAPI integration has been claimed on that evidence alone.

## 5. Regional and topic gaps

| Gap | Existing basis | Next useful work |
| --- | --- | --- |
| Russia primary evidence | Russian independent feeds, English TASS, Ukrainian/international context | Add verified official statements and corporate/procurement records through documented interfaces or deliberate published-file import. Keep government statements as evidence of what was stated, not proof of the claim. English and Russian translations share origin |
| China native and primary evidence | One Chinese CDT aggregator feed plus English SCMP/Nikkei and optional AidData import | Native-language publisher diversity and official statistics, regulatory filings and Taiwan primary releases matter more than another English aggregator. PRC MFA page availability is not an established RSS/API contract. Preserve traditional/simplified Chinese and original organisation identifiers |
| Iran primary evidence | HRANA and IranWire in Persian/English; opt-in OONI; IAEA references | Establish current permitted MFA/IRNA and IAEA document access, add published investigations/datasets, retain Persian original text and calendar evidence. Two translations from one outlet do not double corroboration |
| Africa/Latin America/South Asia | English international sources, Dawn and broad Google/GDELT discovery | Build a verified native-language publisher roster by actual need. Add French/Arabic/Spanish/Portuguese local and public-agency feeds, with stable publisher IDs and health checks. Avoid replacing sparse coverage with guessed place pins |
| Humanitarian | WHO, IFRC, ReliefWeb RSS; optional API | Enable approved ReliefWeb and add HDX administrative context, with dated source metadata and disaggregation limits |
| Companies/procurement | SEC/CH/GLEIF, one UK notice page | Add GLEIF discovery, bounded notice pagination within explicit budget and then Find a Tender/EU TED or published US spending sources after contract verification. Do not claim a global supplier database |
| Cybersecurity | KEV, ransomware claims, IODA and optional OONI | Prioritise country/ASN outages and passive domain context. NVD, URLhaus/ThreatFox, OTX and Shodan are specialist enrichment candidates, not missing geographic news coverage |
| Social | Fixed RSS/watchlists | Add permitted public search only where current access works. X, private Telegram and restricted platform research interfaces are not solved by indiscriminate free-account creation |

The more detailed candidate backlog is
[Regional source expansion](../REGIONAL_SOURCE_EXPANSION.md). Its older status
labels must be read alongside the implemented code and this audit, not as current
operational claims. No newly guessed Russian, Chinese or Iranian feed URL was
added in this research-only work.

## 6. Make best use of sources without slowing the app

1. Expose separate badges for implemented, configured, last successful collection,
   degraded, unsupported for this question, and catalogue/reference only.
2. Keep private research request-driven. Fairly budget across evidence classes,
   languages and original publishers; a dozen editions of one aggregator should
   not crowd out the only original record.
3. Show coverage receipts for time, region, language, item/page cap and provider
   failures. A failed source is not an empty result; empty means no returned
   matches, not that nothing happened.
4. Separate exact-area observations from broader country/place context. Let the
   user see both, with explicit labels, instead of discarding all useful context
   or fabricating precise geography.
5. Preserve original IDs, publisher families, dataset versions and document
   locators through reports. Detect syndicated origin and corrected/retracted
   evidence; do not compute credibility from raw source counts.
6. Use existing guarded HTTP, conditional requests, cooldowns and byte limits.
   Do not expand the live memory store, unbounded history or map symbol count as
   a substitute for indexed/bounded question-time collection.
7. Each new account should have a concrete supported connector, minimum scope,
   a successful normal connection test and a recorded next renewal step. Account
   creation alone is not an integration milestone.

## 7. Verification performed for this document

- Read composition, provider implementations, source seeds, source feasibility,
  regional expansion and area-research operations.
- Calculated seeded feed/language counts using the repository's Python runtime.
- Rechecked current primary API/authentication/eligibility documentation for
  Companies House, SSLMate, UCDP, ACLED, ReliefWeb, SEC, OpenAlex, USGS, EONET,
  GDELT, GLEIF, OONI, HDX HAPI, ITA, Cloudflare Radar, IAEA NEWS and OpenSanctions.
- No new account, credential, backend adapter or production configuration was
  created by this research subtask. No test/build coverage is claimed for this
  documentation-only change. Root audit records onboarding and implementation.
