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
