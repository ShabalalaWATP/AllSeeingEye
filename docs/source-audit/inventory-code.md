# Source integration audit, code baseline

Audit date: 10 September 2026. Baseline: `4528ca6`.

This is an offline implementation inventory, not a claim that every source is
currently reachable or licensed for every use. Factories were inspected with
inert HTTP doubles. No provider requests, account sign-ups, secret values or
database contents were accessed by this audit. The coordinating agent supplied
configuration-presence booleans separately. Concurrent source improvements must
be counted after their implementation, not added to these baseline numbers.

The complete per-ID inventory, implementation references, configuration names,
coverage metadata and stated limits are in [inventory-code.json](inventory-code.json).

> **Superseded in part, 16 September 2026.** Nine sources in this baseline are no longer
> collected: `reddit_worldnews`, `reddit_geopolitics`, `reddit_ukrainianconflict` and the
> six `yt_*` channel Atom feeds, along with their nine `research_social_*` providers. Both
> hosts' `robots.txt` disallow the paths they polled. YouTube coverage was rebuilt on the
> keyed Data API v3 route with 29 channels and one aggregated research provider. See
> [SOCIAL_SOURCE_COVERAGE.md](../SOCIAL_SOURCE_COVERAGE.md). The counts below are the
> 10 September baseline and have deliberately not been rewritten.

## Exact counts and what they mean

| Inventory | Baseline count | Interpretation |
| --- | ---: | --- |
| Possible scheduled source IDs | 82 | Union across public and credentialed alternatives, not simultaneous providers |
| Scheduled IDs with no optional credentials | 79 | Includes two registered but unavailable managed FIRMS connections and two public FIRMS downloads |
| Scheduled IDs with all implemented optional credentials | 79 | Public FIRMS downloads and ReliefWeb RSS are replaced; ACLED/AISStream join |
| Scheduled IDs with reported current development credentials | 78 | AISStream and keyed FIRMS present, other optional credentials absent; before disabled-source controls |
| Research capability IDs | 57 | Includes 13 language editions, derivatives of live RSS feeds and two private-input capabilities |
| Research IDs excluding private imports | 55 | Does not mean 55 independent organisations or 55 universally searchable APIs |
| RSS seeds | 38 | 7 official, 14 outlet, 8 regional, 9 social |
| Camera provider entries | 57 | Mixture of public APIs, published camera inventories, curated links and directories; not camera or working-stream count |
| Explicit area-capable research contracts | 3 | Retained public points, Copernicus rectangles, local historical AidData polygons |

The 82 scheduled IDs comprise 15 disaster, 8 space, 3 cyber, 3 conflict,
7 aviation, 6 humanitarian, 3 maritime, 5 political, 22 news and 10 social IDs.
Organisation/independence keys must be used when assessing corroboration: two
editions, products or mirrors are not two independent witnesses.

Code references: `backend/src/ase/adapters/feeds/registry.py`,
`backend/src/ase/container/__init__.py`,
`backend/src/ase/container/research_sources.py`,
`backend/src/ase/adapters/geo/camera_registry.py`.

## Credential and configuration gaps

Presence below was supplied by the coordinating agent's safe settings audit;
no values are recorded here. A present credential is not a successful test.

| Setting | Present | Existing implementation | Consequence / next action |
| --- | --- | --- | --- |
| `ASE_AISSTREAM_API_KEY` | Yes | Global terrestrial AIS WebSocket | Test existing connection before creating another account. Open-ocean coverage remains incomplete. |
| `ASE_FIRMS_MAP_KEY` | Yes | NOAA-20 and NOAA-21 VIIRS Area API | Test existing key. Two sensor products do not make independent confirmation of a fire. |
| `ASE_UCDP_ACCESS_TOKEN` | No | Token API with public monthly-file fallback | Optional improvement; a free public candidate fallback already exists. Release is fixed by `ASE_UCDP_CANDIDATE_VERSION`. |
| `ASE_ACLED_REFRESH_TOKEN` or `ASE_ACLED_ACCESS_TOKEN` | No | Political violence/protest API | Requires suitable event-data entitlement. Superseded 15 September 2026: a refresh token now renews automatically with encrypted rotation (see `docs/CONFLICT_COVERAGE.md`); a manual access token still expires after 24 hours. |
| `ASE_RELIEFWEB_APPNAME` | No | Humanitarian reports API | Requires approved application name; public ReliefWeb RSS exists meanwhile. An app name is not a secret API key. |
| `ASE_OS_MAPS_KEY` | No | GB OS Road, Outdoor and Light proxy | A valid OS Maps project key would activate the existing styles. |
| `ASE_COMPANIES_HOUSE_KEY` | No | Company search/profile, officers, PSC | One credential activates three bounded registry capabilities. |
| `ASE_CERTIFICATE_TRANSPARENCY_KEY` | No | SSLMate Cert Spotter issuance search | Exact-domain, first-page unexpired certificates only. No full domain investigation follows from adding a key. |
| `ASE_UKSL_SNAPSHOT_PATH` | No | Validated local sanctions snapshot | Import a dated official snapshot; no account is the missing step. |
| `ASE_OFAC_SDN_SNAPSHOT_PATH` | No | Validated local sanctions snapshot | Import a dated official snapshot; no live designation API is wired. |
| `ASE_AIDDATA_CATALOGUE_PATH` | No | Local indexed project catalogue | Prepare a provenance-preserving historical release import; no download occurs automatically. |
| `ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED` | False | Country/day connectivity aggregates | Existing licence gate, not missing credentials. The operator's permitted deployment use must fit the data terms. |
| `ASE_FEEDS_CONTACT` | Genuine contact configured | Public API identification including routing | No contact-address blocker identified by the coordinating agent. |

Neither OpenSky, OpenAQ, Global Fishing Watch, N2YO, Space-Track nor a generic
web-search provider has credential settings or an adapter at this baseline.
Creating their accounts alone would not connect them. OpenAlex is implemented
with anonymous queries and no key setting; its current authentication policy
needs official verification before deciding whether a new key integration is
necessary. Do not rely on the adapter's dated comment as current provider policy.

### Where administrator connection settings really exist

`/admin/sources` supports activation, an isolated 20-second scheduled-feed test,
and circuit reset. It does not expose a generic API-key manager. Research-only
sources require a scoped research query to test. Some optional live connectors
are absent from the catalogue until a server credential exists, so a user cannot
discover every missing connection from that screen alone.

FIRMS has a dedicated draft, test and confirm flow. Its encrypted singleton is
`firms_credentials`, with `active_encrypted`, `draft_encrypted`, revisions and
test/expiry metadata. `ASE_FIRMS_MAP_KEY` takes precedence and makes the stored
connection read-only in the UI. `source_controls` contains activation overrides,
not credentials. Ordinary missing source credentials remain server settings and
require restart. LLM profiles use separate encrypted `llm_profiles` records and
scoped connection bindings; those do not configure data-source accounts.

Safe operational queries should return only existence booleans, revisions,
enabled states and test timestamps. Do not select ciphertext, hints or raw
credentials into an audit report. This worker did not query the database.

Code references: `backend/src/ase/application/admin/source_controls.py`,
`backend/src/ase/adapters/persistence/firms_credentials.py`,
`backend/src/ase/adapters/feeds/firms_runtime.py`,
`frontend/src/features/admin/FirmsConnectionPanel.tsx`.

## What research can actually collect

| Family | Existing use | Material limits |
| --- | --- | --- |
| Google News | 13 question-specific editions; English watchlist polling | Undocumented RSS, first 200 items, publication-date filtering, no full articles, no area contract |
| Official and world outlet RSS | 21 scheduled feeds | Not exposed as on-demand question providers at this baseline; reuse is a concrete missing integration |
| Regional RSS | 8 live feeds plus question providers | 3 Russian, 1 Chinese, 4 Persian/English Iranian editions; local headline phrase matching, bounded recent feed, no full archive |
| Social | 6 YouTube channel feeds, 3 subreddit feeds, 1 Mastodon instance | Configured feeds/tags only, no platform-wide YouTube/Reddit/Telegram/Bluesky search; social research uses only the 9 RSS feeds |
| Company / ownership | SEC, Companies House, GLEIF | Exact identifiers or explicit identity candidates; current profiles/first pages are not verified beneficial ownership histories |
| Domain | Verisign RDAP, Google DNS, SSLMate CT | RDAP only .com/.net; current resolver snapshot; CT first page/exact domain; no historical passive DNS |
| Scholarly | OpenAlex and Crossref | Opt-in first 20 publication metadata results, overlapping upstream content, no full papers or universal country filter |
| Public records | UK Parliament, Contracts Finder, World Bank | Specific UK records/annual series, bounded pages, not global procurement/political coverage |
| Designations | UKSL and OFAC local snapshots | Not configured; candidate name matches require identity resolution |
| China development | AidData local catalogue | Not configured; historical commitment-year records, terms and geometry from imported release |
| Connectivity | OONI country/day, IODA live alerts | OONI licence gate not enabled; no individual probe data or attribution of an outage's cause |
| SEC documents | Explicit CIK/filing selection and bounded extraction | Separate user-selected document flow; metadata collection alone does not read filings |

The 13 Google News editions are English, French, German, Spanish, Arabic,
Russian, Ukrainian, Simplified Chinese, Traditional Chinese, Portuguese,
Japanese, Korean and Hindi. Persian is covered only by the configured Iranian
RSS feeds, not a Google News Persian edition.

## Area research is the largest capability gap

The recent-area drawer chiefly samples precise public points already retained
on the server. It does not refresh each upstream provider. It scans at most
2,000 candidates per event category and retains at most 88 Quick or 264 Detailed
records. Historical backfill, missing categories, unknown dates and imprecise
locations remain explicit gaps. Camera catalogues, camera imagery and packaged
infrastructure are not included.

Most conflict reporting is deliberately not an exact point. UCDP locations are
classified CITY/ADMIN1/COUNTRY, ACLED precision 1/2 is CITY, GDELT uses its own
reported city/region classes and ReliefWeb is country context. These records do
not pass the retained area's `GeoConfidence.EXACT` filter. Consequently the
existence of a conflict feed does not guarantee conflict evidence in an area
report. Add clearly labelled contextual intersection/search, with uncertainty,
rather than relabelling approximate records as exact.

Copernicus is the only existing external recent-area research provider. It
accepts an exact axis-aligned rectangle of at most 10 degrees per side and a
maximum 14-day interval, returning at most 20 Sentinel-2 scene footprints. It
does not search arbitrary polygons or analyse imagery. AidData implements exact
project-polygon intersection in its separate recorded-year historical mode.
The catalogue's statement that precise AidData area search is pending is stale.

Code references: `backend/src/ase/adapters/research/retained_area.py`,
`backend/src/ase/adapters/research/retained_area_selection.py`,
`backend/src/ase/adapters/research_records/copernicus_research.py`,
`backend/src/ase/adapters/research_records/aiddata_provider.py`,
`docs/AREA_RESEARCH.md`.

## Map coverage and provider diversity

- Aviation has seven connector IDs but all query `adsb.lol`. The worldwide
  sweep admits 24 circles per poll; viewport interests admit four. Aircraft
  expire after ten minutes. This is sampled reception, not a simultaneous
  complete global feed. OpenSky and a separately operated ADS-B fallback require
  new implementations and appropriate current terms.
- Maritime has AISStream, Finland's Digitraffic and NGA navigation warnings.
  Warnings are not ship tracks. AISStream is terrestrial reception; military
  vessels may not broadcast identifiable public AIS. Global Fishing Watch would
  add historical vessel/activity context rather than fill all live ocean gaps.
- Space has four CelesTrak products plus launch and SWPC products. Active,
  military and Skynet IDs overlap; they are not independent orbital solutions.
  Positions are propagated estimates from public elements, with ageing checks.
  There is no Space-Track or N2YO backup at this baseline.
- Natural hazards already combine USGS, EMSC, GDACS, EONET, NHC, JTWC, GVP,
  tsunami centres, NWS and two FIRMS sensors. Fresh area/history adapters are
  more immediately useful than duplicating the same feeds under more labels.
- CCTV has 57 provider entries across official/public and curated sources.
  OpenCCTV is limited to three Asian regions; its regional marker limits are
  1,200, 800 and 600. A directory entry does not establish working playback or
  permission to access an arbitrary host. Do not treat more directory markers
  as more imagery available to an LLM.
- Infrastructure is packaged: 1,999 approximate OSM cable segments, 25 ground
  stations and 195 historical WRI nuclear power-plant rows. Cable segments are
  not distinct whole cables. Nuclear power plants do not cover the entire fuel
  cycle or every military nuclear site. These are neither refreshed nor searched
  by the area provider.
- The conflict tracker has 23 curated region locators. Its five frontline
  entries are access links only. No live territorial-boundary feed is connected.
- OpenFreeMap, the EOX 2024 mosaic, OS Maps, Photon, Valhalla, AWS public Terrain
  Tiles and Wayback are context/query services, not additional news evidence
  publishers. GNSS interference is derived from aircraft observations, not an
  independent jamming intelligence provider.

## Recommended delivery order

1. Test and repair the already configured AISStream/FIRMS connections and existing
   no-key sources before adding more polling load. Surface configured, disabled,
   failing, unavailable and unsupported states separately.
2. Reuse the 21 official/world RSS feeds in bounded on-demand questions. Add fresh
   USGS/EONET area searches and explicit area-context capabilities for imprecise
   news/conflict records. Preserve provenance and date/location uncertainty.
3. Complete existing low-friction registrations: Companies House, OS Maps and
   SSLMate. Request ACLED entitlement and ReliefWeb approval only with truthful
   intended-use details. Add credential lifecycle rather than relying on a
   short-lived manually pasted ACLED token indefinitely.
4. Import current dated UKSL/OFAC snapshots and a validated AidData release. These
   improve distinct research areas without another live polling service.
5. Research and implement genuinely different coverage: historical maritime
   activity, independent aircraft reception, broad public web/news search,
   African/Latin American/South Asian local and official sources, country-specific
   corporate/procurement records and geospatial infrastructure context.
6. Build one administrator source connection journey covering all providers,
   test status, account prerequisites, scope, quota and licence limitations.
   Do not equate an enabled toggle with credentials or a successful collection.

Provider-account availability, current terms, fees and permitted reuse still
require official-source research. This code audit does not authorise purchases,
assert account entitlement or establish public deployment readiness.
