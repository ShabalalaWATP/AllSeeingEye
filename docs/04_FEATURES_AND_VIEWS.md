# Features and Views

Status: approved design with an implementation inventory updated on 6 September 2026. Sections 1 to 10 retain design intent except where an implementation is described explicitly. Sections 11 and 12 distinguish working features from follow-ups and upstream/key blockers. "Phase" refers to `05_ROADMAP.md`; operational limits are in [Phase 5 and Phase 6 operations](PHASE5_PHASE6_OPERATIONS.md).

## 1. Application shell

- The app opens on the 3D globe. It is the root route and the default view for every user; Map mode is a toggle from the globe (decision accepted 3 September 2026).
- The brand mark in the top-left of the shell is the React Bits Evil Eye component itself, running live at a small size (see `01_ARCHITECTURE.md` section 5.6).
- Left rail: Globe, Map, Trackers (Conflict, Disaster, Aviation, Maritime, Space, Cyber, Social), Direction (PIRs, AOIs, Indicators), Reports, Admin (admin only).
- Top bar: global search (places, countries, callsigns, MMSI, keywords), time window (live, 1h, 6h, 24h, 72h, 7d), nation filter, live status dot, alert bell, user menu.
- Main canvas: globe or map. Right drawer: inspector (selected event, country, aircraft, vessel) or filters. Bottom: event ticker with grade chips.
- Keyboard first: `/` search, `G` globe, `M` map, `T` time slider, `Esc` clear selection.

## 2. Globe (primary view)

| Feature | Priority | Phase | Notes |
|---|---|---|---|
| Dark globe with atmosphere as the default view, smooth zoom into Mercator map | Must | 0 (empty globe), 1 (data) | MapLibre `globe` projection preset; the globe is the root route |
| Layer manager with per-category toggles, legend and counts | Must | 1 | Driven by the layer registry |
| Event points, clustering at low zoom, H3 hex density for fires and news | Must | 1 | deck.gl |
| Time slider and playback over the retained window | Must | 2 | Filters by observed and published time |
| Nation filter: click a country or pick from a list; every panel reacts | Must | 1 | Natural Earth polygons |
| Country choropleths: news volume, conflict intensity, GDELT tone, disaster alerts | Should | 2 | Server-side aggregates |
| Day/night terminator and sun position | Should | 1 | Cheap, looks superb |
| Aircraft icons with heading, trails, altitude colouring; vessel icons | Must | 3 | Icon layers |
| Satellite orbits and ground tracks for selected satellites | Could | 3 | satellite.js SGP4 in a worker |
| Arcs for relationships (flight origin/destination, story links) | Could | 3 | ArcLayer |
| Areas of interest drawn on the globe, saved per user | Must | 4 | Small polygons in PostGIS |
| "Ops room" idle mode: auto-rotate, ticker, alerts, no chrome | Should | 4 | For a wall screen |
| Lite mode for weak GPUs | Should | 1 | |

## 3. Map mode

| Feature | Priority | Phase |
|---|---|---|
| Base layers: Dark vector, OS Maps Road/Outdoor/Light (GB only), Satellite (Esri), NASA GIBS daily imagery with date picker, Night lights, Hybrid | Must | 1 |
| Optional 3D terrain (free DEM tiles) | Could | 6 |
| Coordinate readout in WGS84, MGRS and OS grid reference; copy on click | Should | 1 |
| Measure distance/area, bearing | Should | 2 |
| Overlays: weather radar (RainViewer), clouds (GIBS), NAVAREA warning areas, NOTAM-derived closures where available | Could | 3 |
| Saved views (bookmarks) | Should | 2 |

## 4. Country dashboard (nation filter)

A single panel that answers "what is going on in X right now": flag and key facts; news feed (local language and English, translated titles); GDELT tone sparkline; conflict events and fatalities trend (ACLED/UCDP); active disaster alerts; FCDO and US State Department travel advice level; sanctions programmes touching the country; internet connectivity status (IODA, Cloudflare Radar); military and interesting flights currently over or near; volcano and earthquake activity; prediction-market questions mentioning the country; one-click "Generate Country Brief".

## 5. Trackers

### 5.1 Conflict tracker
- Curated, admin-editable list of active conflicts and tension areas, each with an AOI, belligerents, related sources (RSS, Telegram channels, ISW layers), and a template mapping.
- Board view: severity, 7-day event count and trend, fatalities, last significant event, latest INTSUM link.
- Detail view (the "specific conflict tracker"): timeline, event map, ISW assessed control layers where public, air-raid alerts (Ukraine, Israel), civilian harm (Bellingcat), strikes (Airwars), related flights and vessels, social feed, and "Generate Conflict Assessment".

### 5.2 Natural disaster tracker
- GDACS, EONET, USGS, EMSC, FIRMS, NHC/JTWC cyclones, volcano reports, NWS/MeteoAlarm warnings, tsunami bulletins.
- Severity board, impact estimates from GDACS, humanitarian response from ReliefWeb and IFRC GO, "Generate Disaster SITREP".

### 5.3 Aviation
- Live civil and military traffic; military and "interesting" filters (community database flags, callsign patterns such as RCH, FORTE, JAKE, NATO, HOMER); emergencies (7700/7600/7500); per-country military activity counts against baseline.
- GNSS interference heat map computed from ADS-B integrity fields, updated hourly (our own GPSJam equivalent).
- Aviation incidents feed; NOTAM-derived airspace closures if a free source proves stable.

### 5.4 Maritime
- AIS in subscribed boxes (chokepoints: Hormuz, Bab el-Mandeb, Suez, Malacca, Taiwan Strait, Bosphorus, Baltic approaches, Panama, GIUK), vessel counts versus baseline.
- Global Fishing Watch events: AIS gaps ("going dark"), loitering, encounters, port visits.
- NAVAREA warnings (exercises, missile test areas, GNSS interference notices), anti-shipping activity messages, UKMTO incidents.

### 5.5 Space
- Satellites over an AOI now and next passes; launch schedule; re-entries; space weather (flares, geomagnetic storms); "which imaging satellites can see this spot today".

### 5.6 Cyber
- CISA Known Exploited Vulnerabilities, ransomware victims by country and group, internet outages and shutdowns (IODA, Cloudflare Radar) on the globe, threat intel feed summaries.

### 5.7 Social listening

- Built: Mastodon hashtag timelines from the packaged instance watchlist, Reddit subreddit Atom feeds and six outlet YouTube channel feeds. Bluesky remains deferred after repeated 403 responses; Telegram is excluded by decision.
- `/trackers/social` shows the retained day's posts by platform and instance, top hashtags, the latest 50 posts and counts of located posts. Located events use the existing social globe category; upstream posts without coordinates are not assigned guessed positions.
- Keyword bursts compare the previous complete UTC hour with sampled history from the preceding 30 days. Up to 32 watchlist/collection terms have durable hourly count aggregates. A burst requires six baseline hours, three posts and at least twice the mean. Personal collection terms are restricted to their owner or an administrator; team terms follow current team membership. Inactive owners, removed members and archived teams stop background collection.
- Mastodon and Reddit begin at reliability E and credibility 6. Named outlet YouTube channels retain outlet reliability. Translation and activity spikes do not establish truth or increase a grade.

## 6. Stories and the ticker
- Built: near-duplicate detection groups related topics. Topic matches and declared publisher groups do not establish independent corroboration. Ambiguous or conflicting headlines remain unconfirmed; instrument metadata supports only provisional grading. See the current doctrine document.
- Proposed: an analyst-reviewed developing-story workflow. There is no automatic claim-verification system.
- Ticker shows the newest graded items; click to fly the globe to the location.
- Built in Phase 5: language detection fills missing languages; a background queue optionally translates foreign-language titles through an enabled `translation` model profile. Original titles remain available and English display titles are streamed to open pages. No real model has been exercised on the development host.

## 7. Direction: PIRs, AOIs, Indicators and Warning
- Collection plan: a named question set (Priority Intelligence Requirements) broken into specific requirements and indicators, each with keywords, categories, AOIs, countries and sources.
- Built: plan pages match current evidence on demand and generate plan-scoped assessments. Continuous PIR tagging and a globe plan filter remain follow-ups.
- Built: indicators evaluate event counts against configured thresholds, with in-app, stream, optional webhook and report routes. Baseline-relative thresholds and email routing remain follow-ups.
- Scheduled products: daily INTSUM at 06:00 for chosen AOIs, weekly conflict roll-ups.
- Built in Phase 5: Google News RSS keyword collection from enabled plans, bounded to 12 literal search terms and 48 requests/hour. The initial edition is GB English. Legacy embedded publisher URLs are decoded only for cited evidence; modern opaque links retain their original Google URL. Article scraping is excluded.

## 8. Reports (Dissemination)
- Template gallery, generation wizard (scope, window, sources, model profile), streaming progress, reader with hover citations and grade badges, version history, "what changed since the previous report", share with other users (object-level permissions), export to Markdown, PDF and DOCX, print stylesheet.
- "Ask the Eye": a free-form question turned into a structured assessment with evidence selection visible to the user before generation.
- Built in Phase 6: PDF and DOCX downloads for a selected frozen version, including grades, citations, provenance and review warnings. Rendering is local and fetches no external resources. DOCX retains Unicode; unsupported characters in the bundled PDF font are written as explicit `[U+XXXX]` code points. DOCX structure is tested, but visual validation in LibreOffice remains unavailable on this host.
- Built in Phase 6: structured comparisons between two versions of the same report, including evidence additions/removals, grade changes, direction, advocacy and validation findings. This is a deterministic field comparison, not a model judgement about change.
- Built in Phase 6: "Find related reports" uses an explicitly configured `embeddings` profile. Indexing is requested in batches of eight from the caller's newest 1,000 visible saved reports. A shared 1,000-vector capacity is checked before model calls; another team's vectors are not evicted to satisfy the request. Live events are never indexed. Similarity scores are not analytical confidence ratings; stale versions and incompatible model fingerprints are excluded.

## 9. Admin
- Users: approve account requests, roles, disable, force reset, sessions.
- LLM profiles: multiple OpenAI-compatible endpoints, with assessment, direction, devil, translation and embeddings roles, connection testing and usage records. Translation and embeddings require enabled profiles and `ASE_ENCRYPTION_KEY`.
- Built in Phase 6: optional administrator TOTP at `/admin/security`, password-confirmed enrolment/removal, replay protection and a host-only recovery command. See the operations guide for recovery and session behaviour.
- Source registry: enable/disable, reliability baseline, poll interval, category, language, credentials, licence note, health.
- Retention and budgets for the live store; snapshot on/off.
- SMTP and webhook settings; branding; audit log; system health.

## 10. Deliberately out of scope for now
- Mobile-native apps, multi-tenant organisations, paid data sources, article/page scraping, storing raw feed history, user-to-user chat.

## 11. Map feature inventory (6 September 2026)

Implementation status through Phases 5 and 6, using the dated feed probes in section O of `02_DATA_SOURCES.md`. "Built" means the current code implements the feature. "Next" means follow-up work; a successful upstream probe alone does not establish an implementation. "Key" needs an operator-obtained free key. "Open" means the source is not confirmed.

| Feature on the globe or map | Feed | Status |
|---|---|---|
| Event points per category sized by severity, inspector with grade and provenance, ticker, per-category switches and counts | Every connector: USGS, GDACS, EONET, SWPC, CISA KEV, 21 RSS and Atom feeds, GDELT 2.0 events, adsb.lol military | Built |
| Nation filter with fly-to, country panel with counts and latest items | Natural Earth polygons | Built |
| Base layers: Dark, Streets, Light, Satellite, Hybrid, OS Road, Outdoor and Light | Keyless except OS Maps | Built (OS Maps needs the key) |
| Day and night terminator, lite mode, WGS84 readout that copies | Local computation | Built |
| Military aircraft and heading icons | adsb.lol `/v2/mil` | Built; historical trails remain a follow-up |
| Interesting, LADD and PIA aircraft | adsb.lol `/v2/ladd`, `/v2/pia` and `dbFlags` | Built |
| Civil traffic over watched areas | adsb.lol `/v2/point/{lat}/{lon}/{radius}` up to 250 nm, no key | Built; OpenSky fallback remains a follow-up |
| Emergency squawks 7700, 7600 and 7500 | adsb.lol `/v2/sqk/{code}` | Built in the aviation board and globe |
| GNSS interference grid using the GPSJam-style proportion | `nac_p` in adsb.lol observations, rolling hourly buckets | Built with one-degree square cells |
| Tropical cyclone positions | NHC RSS and JTWC warning text | Built |
| Volcanic activity, weekly | Smithsonian GVP RSS with `georss:point` | Built |
| Tsunami bulletins | NTWC and PTWC Atom with coordinates | Built |
| EMSC earthquakes | EMSC FDSN JSON | Built |
| US severe weather events | NWS alerts API | Built; Met Office and MeteoAlarm parsers remain follow-ups |
| Daily satellite imagery with a date picker, night lights, GOES GeoColor every ten minutes | NASA GIBS WMTS; tiles verified for VIIRS true colour, the VIIRS day and night band and GOES-East GeoColor | Next |
| Weather radar overlay | RainViewer, two hours of history | Could |
| NAVAREA warning positions | NGA broadcast warnings JSON, positions parsed from warning text | Built |
| Anti-shipping incidents | NGA ASAM answers 404 on every documented path; UKMTO is a link-out | Open |
| Vessels at chokepoints, dark vessels, loitering, encounters | AISStream (key), Global Fishing Watch (token) | Key |
| Satellite and ISS positions | CelesTrak GP JSON propagated with SGP4 | Built; ground tracks and pass predictions remain follow-ups |
| Launch sites and upcoming launches | Launch Library 2 | Built |
| Planetary K index and space weather | SWPC JSON | Built; aurora oval overlay remains a follow-up |
| Internet outages by country | IODA alerts | Built |
| Ransomware victims by country | ransomware.live recent victims | Built |
| Located social posts and translated display titles | Retained social events and optional translation profile | Built; current social feeds usually have no coordinates |
| Conflict events | GDELT 2.0 events (built); HDX HAPI monthly aggregates by admin area | Built; aggregates next |
| Assessed control of terrain in Ukraine | ISW ArcGIS: only historical feature services are discoverable; no current daily service found | Open |
| Air-raid alerts by oblast | alerts.in.ua (token) over geoBoundaries ADM1 polygons | Key |
| Active fires | NASA FIRMS (key by email) | Key |
| Infrastructure on demand: airfields, ports, power stations | Overpass API | Later |
| Country choropleths: news volume, conflict intensity, disaster alerts, outages, attention | Live store aggregates, IODA, Wikipedia page views | Next |
| Time-window filter over retained events | Live store | Built; playback remains a follow-up |
| Grid clustering at low zoom | deck.gl | Built; H3 density is not implemented |
| Saved areas of interest | Bounding boxes or country sets | Built in Direction; drawing/editing on the globe remains a follow-up |
| Arcs for story links and flight origin and destination | Live store | Later |
| Ops room idle mode | Local | Built |

## 12. Analysis and hardening inventory (6 September 2026)

| Capability | Implemented scope |
|---|---|
| Doctrine and provenance | Conservative reliability/credibility grading, topic clustering, frozen selected evidence with hashes and translated-title provenance, strict new-response validation, per-judgement support ceilings and optional Wayback archiving. Automated checks do not verify claims or replace analyst review |
| Report production | INTSUM, INTREP, Country Brief, Ask the Eye, Disaster SITREP, Conflict Assessment, Aviation Activity, Maritime Activity and Cyber Summary; direction and optional devil's advocacy passes |
| Tracker analysis | Hazard and curated conflict boards/details; aviation, maritime, space, cyber and social boards computed from retained events |
| Baselines | Tiny durable hourly aviation and configured social-keyword aggregates; GNSS observations remain in memory |
| Direction and warning | Saved areas/plans, on-demand evidence per SIR, plan-scoped reports, threshold indicators, alerts, acknowledgement and scheduled products |
| Social and languages | Mastodon/Reddit/YouTube feeds, social board, keyword bursts, language detection and optional title translation |
| Keyword collection | Enabled plan terms feed bounded Google News RSS queries. Legacy cited URLs can resolve locally; opaque modern URLs remain unchanged |
| Export and change review | Markdown/PDF/DOCX downloads and deterministic version comparison, including frozen evidence and validation changes |
| Semantic report search | Explicit batches of eight, personal/team visibility on counts and results, shared 1,000-vector capacity checked before calls, portable JSON vectors and a configured embeddings endpoint |
| Accounts and teams | User, manager and administrator roles; own account details and password changes at `/account`; explicit team membership, designated managers, personal/team scope on saved operational work, late permission checks, fresh stream authority and scoped client cache invalidation |
| Administrator security | Optional TOTP, encrypted enrolment secrets, replay checks, password-confirmed management and host-only recovery |
| Recovery | Verified SQLite/PostgreSQL backup bundles and restore to new destinations; [backup operations](BACKUP_RESTORE.md) describe testing and limits |
| Performance and accessibility | Separate MapLibre/deck.gl build chunks, bounded export/model concurrency, live-store pruning, mobile navigation with native modal focus management and a keyboard skip-to-content link; these changes do not establish a complete performance or accessibility certification |
| Security assessment | [Phase 6 ASVS review](security/PHASE6_ASVS_REVIEW.md) records findings, verification and remaining deployment checks; it is not an ASVS level 2 certification or approval for public exposure |

The broader [improvement plan](MASTER_FIX_IMPROVEMENT_PLAN.md) records the current security, team, analytical and visual changes. Remaining work is tracked in the master plan: PIR pipeline tags and globe filtering, richer collection-plan editing, baseline-relative indicators, email transport, deferred feed parsers and keys, sanctions/context enrichment, contradiction handling, and further globe overlays. Warning Report, Competing Hypotheses and Source Evaluation templates are not in the implemented template set above.

Operational validation is incomplete where it needs the operator's environment: no real LLM/embeddings endpoint has been configured and exercised, modern Google News link resolution is unavailable without a permitted API, DOCX visual rendering requires a suitable office renderer, and an operator recovery drill is still required. A synthetic PostgreSQL recovery drill passed before this team-scope milestone; the newer schema also needs recovery verification before operational use. The [operations guide](PHASE5_PHASE6_OPERATIONS.md) separates those limitations from the implemented behaviour.
