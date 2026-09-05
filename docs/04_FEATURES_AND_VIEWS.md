# Features and Views

Status: proposal. MoSCoW priorities are suggestions for Alex to prune. "Phase" refers to `05_ROADMAP.md`.

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
- Bluesky, Mastodon, Reddit, YouTube channel uploads, and public Telegram channels tied to conflicts; keyword and hashtag watchlists; burst detection; everything defaults to reliability E/F and credibility 6 until corroborated.

## 6. Stories and the ticker
- Near-duplicate detection groups items into stories; the corroboration count of a story and the mix of independent sources drive its credibility grade.
- "Developing" badge when several independent sources publish within a short window.
- Ticker shows the newest graded items; click to fly the globe to the location.

## 7. Direction: PIRs, AOIs, Indicators and Warning
- Collection plan: a named question set (Priority Intelligence Requirements) broken into specific requirements and indicators, each with keywords, categories, AOIs, countries and sources.
- The pipeline tags events against PIRs continuously; the PIR page shows the evidence gathered and can generate a targeted assessment.
- Indicators board: user rules ("military flights in AOI above 2x baseline", "FIRMS hotspots in AOI", "Polymarket probability above 30%", "air-raid alert in oblast", "internet outage in country") with traffic-light status, history and alert routing (in-app, email, webhook).
- Scheduled products: daily INTSUM at 06:00 for chosen AOIs, weekly conflict roll-ups.

## 8. Reports (Dissemination)
- Template gallery, generation wizard (scope, window, sources, model profile), streaming progress, reader with hover citations and grade badges, version history, "what changed since the previous report", share with other users (object-level permissions), export to Markdown, PDF and DOCX, print stylesheet.
- "Ask the Eye": a free-form question turned into a structured assessment with evidence selection visible to the user before generation.

## 9. Admin
- Users: approve account requests, roles, disable, force reset, sessions.
- LLM profiles: multiple OpenAI-compatible endpoints, per-role routing (assessment, fast, embeddings), test-connection button, token budgets, cost tracking.
- Source registry: enable/disable, reliability baseline, poll interval, category, language, credentials, licence note, health.
- Retention and budgets for the live store; snapshot on/off.
- SMTP and webhook settings; branding; audit log; system health.

## 10. Deliberately out of scope for now
- Mobile-native apps, multi-tenant organisations, paid data sources, scraping sites that offer no feed or API (policy question for Alex), storing raw feed history, user-to-user chat.

## 11. Map feature inventory (5 September 2026)

Status after Phases 0 to 2, checked against live feeds on 5 September 2026 (section O of `02_DATA_SOURCES.md`). "Built" is on the globe today. "Next" is scheduled in `MASTER_IMPLEMENTATION_PLAN.md` with a feed that answered. "Key" waits only for a free key that Alex has to obtain. "Open" means the source is not confirmed and the feature is not promised.

| Feature on the globe or map | Feed | Status |
|---|---|---|
| Event points per category sized by severity, inspector with grade and provenance, ticker, per-category switches and counts | Every connector: USGS, GDACS, EONET, SWPC, CISA KEV, 21 RSS and Atom feeds, GDELT 2.0 events, adsb.lol military | Built |
| Nation filter with fly-to, country panel with counts and latest items | Natural Earth polygons | Built |
| Base layers: OpenFreeMap dark, EOX Sentinel-2 cloudless, hybrid, OS Maps Road, Outdoor and Light | Keyless except OS Maps | Built (OS Maps needs the key) |
| Day and night terminator, lite mode, WGS84 readout that copies | Local computation | Built |
| Military aircraft | adsb.lol `/v2/mil` (96 aircraft at the time of the check) | Built as points; heading icons, altitude colour, trails and callsign labels are next |
| Interesting, LADD and PIA aircraft | adsb.lol `/v2/ladd`, `/v2/pia` and `dbFlags` | Next |
| Civil traffic over areas of interest | adsb.lol `/v2/point/{lat}/{lon}/{radius}` up to 250 nm, no key; OpenSky anonymous bounding boxes, 400 credits a day | Next |
| Emergency squawks 7700, 7600 and 7500 as alerts | adsb.lol `/v2/sqk/{code}` | Next |
| GNSS interference hex map (the GPSJam method) | `nac_p` and `nic` fields present in adsb.lol responses | Next |
| Tropical cyclones with centre, intensity and movement | NHC RSS `nhc:Cyclone` elements (Atlantic and East Pacific); JTWC RSS plus warning text with "NEAR 26.2N 127.5E" positions (West Pacific and Indian Ocean) | Next |
| Volcanic activity, weekly | Smithsonian GVP RSS with `georss:point` | Next |
| Tsunami bulletins | NTWC and PTWC Atom with `geo:lat` and `geo:long` | Next |
| Earthquakes outside the US within seconds of detection | EMSC FDSN JSON | Next |
| Severe weather polygons | NWS alerts API (polygons on some alerts, US only); Met Office UK warnings Atom | Next |
| Daily satellite imagery with a date picker, night lights, GOES GeoColor every ten minutes | NASA GIBS WMTS; tiles verified for VIIRS true colour, the VIIRS day and night band and GOES-East GeoColor | Next |
| Weather radar overlay | RainViewer, two hours of history | Could |
| NAVAREA warning positions and areas | NGA broadcast warnings JSON (386 active); positions parsed from the warning text | Next |
| Anti-shipping incidents | NGA ASAM answers 404 on every documented path; UKMTO is a link-out | Open |
| Vessels at chokepoints, dark vessels, loitering, encounters | AISStream (key), Global Fishing Watch (token) | Key |
| Satellites over an area, ground tracks, the ISS | CelesTrak GP JSON propagated with SGP4 | Next |
| Launch sites with a countdown | Launch Library 2, 15 calls an hour | Next |
| Aurora oval and planetary K index | SWPC ovation and K-index JSON | Next |
| Internet outages by country, region and network | IODA alerts | Next |
| Ransomware victims by country | ransomware.live recent victims | Next |
| Conflict events | GDELT 2.0 events (built); HDX HAPI monthly aggregates by admin area | Built; aggregates next |
| Assessed control of terrain in Ukraine | ISW ArcGIS: only historical feature services are discoverable; no current daily service found | Open |
| Air-raid alerts by oblast | alerts.in.ua (token) over geoBoundaries ADM1 polygons | Key |
| Active fires | NASA FIRMS (key by email) | Key |
| Infrastructure on demand: airfields, ports, power stations | Overpass API | Later |
| Country choropleths: news volume, conflict intensity, disaster alerts, outages, attention | Live store aggregates, IODA, Wikipedia page views | Next |
| Time slider and playback over the retained window | Live store | Next |
| Clustering and hex density at low zoom | deck.gl | Next |
| Areas of interest drawn on the globe and saved per user | PostGIS | Phase 4 |
| Arcs for story links and flight origin and destination | Live store | Later |
| Ops room idle mode | Local | Phase 4 |

## 12. Analysis feature inventory (5 September 2026)

Built: NATO grading (reliability from the registry, credibility from corroboration, syndication folded), story clustering, evidence freezing with hashes and Wayback archives, the quality of information check with a confidence ceiling, doctrine-validated products (INTSUM, INTREP, Country Brief, Ask the Eye) with the PHIA yardstick and a separate confidence rating, versions with a "what changed" line, a direction call that turns a question into PIR, SIRs and EEIs and steers evidence selection, a devil's advocacy pass that can only lower confidence, instruction-like text screened out of evidence, usage and audit logs.

Next, in the order the master plan schedules them:

1. Tracker boards for hazards, curated conflicts, aviation, maritime warnings, space and cyber: activity now against the week before, trend, worst and latest event, countries touched, and a detail view with a timeline and the events themselves.
2. Baselines for anomaly detection: tiny hourly aggregates (military flights per country, emergency squawks, jam percentages, outage alerts) so that "above twice the baseline" has a baseline. This is the one new durable table the architecture allows for "normal levels".
3. Products: Disaster SITREP, Conflict Assessment, Aviation Activity Report, Maritime Activity Report, Cyber Summary, Warning Report, Competing Hypotheses, Source Evaluation.
4. Direction and warning: areas of interest, collection plans with PIRs, keyword collection through Google News RSS queries and social watchlists, event tagging to PIRs, an indicators board with traffic lights over tracker signals and Polymarket probabilities, alert routing in-app and by webhook, scheduled INTSUMs.
5. Context for briefs: sanctions programmes touching a country (UK Sanctions List XML and OFAC SDN XML), appeals and outbreaks (IFRC GO, WHO Disease Outbreak News, UNHCR), weather (Open-Meteo), attention (Wikipedia page views and the current events portal).
6. Grading depth: contradiction rules (doubtful and improbable), instrument anomaly flags, corroboration and contradiction identifiers on events, and an evidence preview before generation for asks.
7. Hardening: report diffing, semantic search over reports, PDF and DOCX export, backups.
