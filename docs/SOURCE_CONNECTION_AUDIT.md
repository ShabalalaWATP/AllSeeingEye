# Source connections and coverage audit

Checked 10 September 2026 against the repository, local configuration, targeted
provider requests and current official access documentation. Baseline commit:
`4528ca6`. This document separates implemented connectors, configured access,
observed delivery and work still needed. A catalogue entry is not a connection.

## Findings that matter

The app has a broad catalogue, but the main gaps are operational access,
independent coverage and use of existing material in private research.

- The baseline contains **82 possible scheduled source IDs**, including
  mutually exclusive alternatives, **57 research capabilities** and **57 camera
  provider entries**. Current development settings select 78 scheduled sources
  before runtime health is considered. These are not 192 independent sources.
- All seven aircraft connectors use **adsb.lol**. Regional subscriptions and a
  military endpoint improve sampling but do not provide provider redundancy.
- The 38 RSS seeds contain seven official/context feeds, 14 general outlets,
  eight regional feeds and nine social feeds. Their configured languages are
  32 English, three Russian, one Chinese and two Persian. Native-language and
  primary-record coverage needs more work than another English aggregator.
- The infrastructure snapshot contains 1,999 cable **segments**, 25 ground
  stations and 195 historical nuclear power-plant entries. Segment counts must
  not be advertised as independent cables or worldwide completeness.
- Camera provider families already cover those inspected in OSIRIS. Missing
  credentials, failed endpoints and regional sparsity explain important gaps.
  A camera catalogue entry does not prove its image or stream is available.
- Many conflict/news observations only have city, regional or country locations.
  Exact-area research correctly excludes these. A separate, clearly labelled
  regional-context search is needed, rather than pretending those coordinates
  identify an incident inside a small polygon.

The full machine-readable baseline is
[inventory-code.json](source-audit/inventory-code.json); the accompanying
[code audit](source-audit/inventory-code.md) records exact IDs and adapter paths.

## What was connected or repaired in this run

1. Added all **21 existing official/general publisher feeds** to on-demand
   headline research. Questions stay private; supplied terms are matched locally.
   No article bodies, media or extra redistribution rights are assumed.
2. Interleaved official, outlet, regional and social feed families so a short
   request budget does not consume one whole family first. The request, item
   and duration limits remain unchanged. Providers can still be selected
   explicitly. The catalogue now has **80 research capabilities**, including
   private imports and capabilities that need configuration.
3. Added fresh **USGS FDSN earthquake** and **NASA EONET hazard** searches for
   drawn areas. Each makes one bounded request, followed by exact local geometry
   and time filtering. They support intervals of at most 14 days and 50 Quick
   or 100 Detailed candidates. EONET includes open and closed events. These are
   current catalogue responses for selected dates, not complete historical archives.
4. Preserved original observation identities across fresh and retained data,
   with fresh evidence considered first. Parent-source disabling controls the
   new research routes before and after collection. Legacy EONET polygon centres
   are excluded from retained exact-area evidence unless valid original incident
   point geometry is present.
5. Preserved existing explicit research tasks when a larger catalogue reaches
   the 64-task presentation limit. Only unused or unsupported presentation rows
   may be omitted; selected supported work and explicit tasks are retained.
   Genuinely oversized selected plans still fail before collection.
6. Corrected SCMP to its directly working HTTPS feed address with a trailing
   slash. Private collection continues to refuse redirects.
7. Added a narrowly scoped, size-bounded gzip reader for the two UN RSS endpoints
   that return gzip despite an identity request. Other feed responses keep their
   existing encoding policy. Compressed and expanded sizes are both bounded.
8. Added an AISStream warning when subscription confirmation explicitly reports
   compression disabled. Valid positions are retained. Merely requesting
   compression is not reported as proof that it was negotiated. This matters
   because the provider now describes bandwidth dropping for uncompressed
   connections. [AISStream documentation](https://aisstream.io/documentation).

No extra always-on research polling, dependencies, database migration, provider
account or production deployment was introduced.

## What was actually checked live

| Check | Observed result | Limit of the result |
| --- | --- | --- |
| Existing NASA FIRMS key | Connected; 45 valid NOAA-20 observations in a UK rectangle | Two UTC calendar days, one bounded query; does not establish global coverage |
| USGS fresh area search | Connected; 50 earthquake records and explicit page-truncation receipt | California rectangle, preceding seven days; no second page fetched |
| EONET fresh area search | Connected; one hazard record | Same area/dates; an empty area elsewhere would not establish safety |
| Existing 38 RSS seeds | Initial audit parsed 33, with 1,396 bounded items | Four concurrent requests, 15-second deadlines, one attempt per feed |
| SCMP private research after repair | Connected; 13 matching headlines, one request, no summaries | Public keyword China over 14 days; headlines are unassessed claims |
| UN News / UN Press after repair | Connected; 30 and 10 items, all with recognised publication dates | One fresh GET each; recorded separately from the initial 38-feed audit |
| Gmail account recovery search | Connector available; prior FIRMS registration located | Narrow provider searches found no other matching registrations; not proof that none exist |
| Stored AI profile | One credential-bearing profile exists, disabled, never connection-tested | Audit context could not decrypt it; model access and report generation remain unverified |
| Browser account registration | Blocked before reaching any provider form | Computer-use browser service failed to start because its app-server path was missing |

The initial RSS failures were UN News and UN Press (unsupported encoding) and
three Reddit feeds (HTTP 429, not retried). Post-repair UN results are recorded
separately in [RSS health](source-audit/rss-health.md) and its JSON evidence,
preserving the initial observation.

Six successfully fetched feeds produced 311 items without recognised publication
timestamps. Private dated research excludes them. Feed modification time or
collection time must not be substituted for publication time. A future distinct
"current advisory context" mode could make this material useful honestly.

Evidence: [FIRMS probe](source-audit/firms-health.json),
[area probes](source-audit/area-hazard-health.json),
[RSS probe](source-audit/rss-health.json),
[AI readiness](source-audit/llm-readiness.md). Probe records contain statuses and
counts, not credentials or downloaded articles. AISStream's key is configured,
but a new live WebSocket probe was deliberately not run alongside the feed worker.

## Credentials and datasets still needed

No source activation overrides were present in the local database. The genuine
operator contact is configured. Credential presence was checked without recording
secret values. All paths below are backend settings, not browser environment values.

| Source | Current status | Exact next step |
| --- | --- | --- |
| AISStream | Environment key present | Existing stream remains configured; measure actual delivery and interruptions in source health |
| NASA FIRMS | Environment key present, connection verified | Keep current configuration; encrypted administrator override is not active |
| Ordnance Survey | `ASE_OS_MAPS_KEY` absent | Create an OS Data Hub **OpenData** project and Maps API key; existing proxy then needs an actual tile test |
| Companies House | `ASE_COMPANIES_HOUSE_KEY` absent | Developer account/application and read-only REST key; test company, officers and PSC routes |
| SSLMate CT Search | `ASE_CERTIFICATE_TRANSPARENCY_KEY` absent | Obtain the CT Search API credential; do not substitute a paid certificate-monitoring trial |
| UCDP | `ASE_UCDP_ACCESS_TOKEN` absent | Request authorised token access; retain the existing Candidate CSV fallback and its temporal limits |
| ACLED | `ASE_ACLED_ACCESS_TOKEN` absent | Confirm event-level entitlement before configuring; Gmail Open access is aggregated and does not unlock the event adapter |
| ReliefWeb | `ASE_RELIEFWEB_APPNAME` absent | Obtain an approved application name, not a publishing API key |
| UK sanctions / OFAC SDN | Both snapshot paths absent | Import dated primary lists through the existing validated snapshot process and retain source hash/licence |
| AidData projects | Catalogue path absent | Prepare the supported local catalogue with recorded years, provenance and actual project geometry |
| OONI aggregates | Licence acknowledgement false | Confirm appropriate non-commercial use before enabling; no token is missing |
| OpenAlex | Anonymous basic queries supported; no key setting yet | Free account can raise quota, but a guarded optional-key adapter change is needed before linking |
| AI reports | Disabled, untested saved profile | Use the administrator model-discovery, test and activation journey with usable encryption configuration |

See the [research access audit](source-audit/research-access-gaps.md) for official
onboarding references and eligibility details. OpenAlex documents both anonymous
basic use and a free key with a larger budget; it must not be described as wholly
unavailable without a key. [Current OpenAlex authentication](https://help.openalex.org/api/authentication/).

## Ranked expansion and account queue

Account creation alone does not activate sources without an adapter. Free access
also does not establish redistribution rights, complete coverage or independence.

| Priority | Addition | Why it helps | Access / implementation remaining |
| --- | --- | --- | --- |
| 1 | OS OpenData and Companies House | Makes existing map styles and UK company research usable | Accounts/keys, existing connectors, bounded smoke tests |
| 1 | WSDOT and Alberta 511 | Repairs known North American camera gaps | Authorised codes/keys and adapter updates; WSDOT offers an email access-code form |
| 1 | ReliefWeb and UCDP | Better humanitarian and documented conflict context | Approved appname/token, truthful geographic precision and freshness |
| 1 | Fresh FIRMS area research | Uses the already verified key for requests beyond retained data | New private provider with credential-generation guard, sensor/date budgets and thermal uncertainty |
| 2 | BarentsWatch AIS | Independent complementary Norwegian/Arctic terrestrial and satellite AIS | Account/OAuth client and new adapter; regional, not worldwide |
| 2 | MET Norway Locationforecast | Global forecast context without another key | New small-area sampling adapter, issue/valid times and attribution |
| 2 | Copernicus Data Space imagery | Dated optical/radar evidence rather than more duplicate orbital elements | Existing footprints first; account, bounded preview processing and storage design for imagery |
| 2 | OpenAQ | Adds actual environmental measurements | Free individual key, station coverage, units and per-dataset licence handling |
| 2 | HDX HAPI / IOM DTM | Administrative-level humanitarian needs and displacement | Identifier/subscription, new connectors; never infer household coordinates |
| 2 | GLEIF discovery and primary sanctions imports | Improves company identity resolution and screening evidence | Reuse existing records adapters; add explicit identity-candidate discovery |
| 3 | Cloudflare Radar | Adds another outage/traffic perspective to IODA/OONI | Least-privilege Radar Read token and adapter; observed sample, not all traffic |
| 3 | SatNOGS / NASA GIBS | Public reception-network context and dated map imagery | Separate labelled datasets, source credit and bounded map/research integration |

Official access references: [OS Data Hub](https://osdatahub.os.uk/),
[Companies House developer hub](https://developer.company-information.service.gov.uk/),
[WSDOT access-code form](https://www.wsdot.wa.gov/traffic/api/),
[BarentsWatch developer information](https://developer.barentswatch.no/),
[MET Norway terms](https://api.met.no/doc/TermsOfService),
[OpenAQ getting started](https://docs.openaq.org/),
[Copernicus APIs](https://documentation.dataspace.copernicus.eu/APIs.html).
Further quotas and source-specific terms are in the
[transport/environment audit](source-audit/transport-environment-access.md).

OpenSky needs a written agreement for operational REST use. Global Fishing Watch
requires genuine organisational eligibility and non-commercial use; ASFINAG needs
partner access. Do not create accounts with invented affiliations or treat a
public demo as permission to reuse its underlying data. No such accounts were
created in this run.

## How to make the wider catalogue useful

1. Expose separate connection states: needs credentials, needs approval, ready,
   delivering, empty, stale, rate-limited, unsupported scope and failed. Do not
   collapse them into one green "connected" badge.
2. Extend the existing administrator test/confirm pattern beyond FIRMS to typed
   provider credentials. Keys stay encrypted/server-side; tests disclose no key,
   activation records scope and a source disable switch governs every derivative.
3. Add regional context beside exact-area evidence. Report the relationship
   explicitly: within area, intersects area, city context or country context.
   Include precision and do not let model text silently promote a context record.
4. Rank collection by question, language, period, country and actual capability,
   with bounded request budgets. Publish receipts for unqueried sources and
   truncation rather than claiming a search of the whole Internet.
5. Group repeats by original publisher, event, sensor and registry. Reprinting
   the same wire story or receiving the same AIS message through two providers
   must not increase confidence as two independent confirmations.
6. Keep reports and map caches separate. Query heavier records and imagery on
   demand; use cancellation, shared quotas, backoff and bounded workers. Source
   expansion must not undo the work preventing dashboard freezes.

## Remaining acceptance gates

- Restore the computer-use browser service, then complete eligible free account
  journeys using the authorised contact. No new registrations were completed.
- Resolve administrator AI connection readiness and run a real, cited report
  evaluation; a populated evidence batch is not a tested LLM report.
- Add provider-specific connectors for queued sources and confirm actual access,
  rights, limits, provenance and source-disable behaviour before marking them live.
- Measure regional coverage over time. These point-in-time probes do not show
  continuous delivery or exhaustive worldwide coverage.
- Rotate credentials previously shared in chat through their provider accounts
  before broader deployment. No credentials were rotated during this audit.

Final affected-backend validation passed **304 tests** with **96.26% targeted
statement/branch coverage**, above the unchanged 90% gate. Whole-backend Ruff,
format checking, strict mypy and both import-linter contracts passed. Scoped
Bandit and independent correctness/security review passed after the two
identified area/plan regressions were fixed. File-length checks passed with the
existing untouched 380-line MapLibre engine warning. No frontend source changed.

The first combined coverage invocation failed during NumPy import before tests
ran. Using the standard package coverage source with a report include list
avoided early dotted-module imports; the complete affected group then passed.
No full-backend suite, real-model evaluation or browser/GPU acceptance is claimed.
There is no configured Git remote, and no push or production deployment is claimed.
