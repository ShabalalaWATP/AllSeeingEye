# Data Source Catalogue

Current operational audit: [10 September source connections and coverage](SOURCE_CONNECTION_AUDIT.md).
Use that audit for configured keys, observed delivery, account eligibility and
implemented private research. The historical candidate tables below are not
current activation instructions. In particular, OpenSky operational REST use
requires a written agreement; airplanes.live is not a wired fallback, and all
seven current aviation connectors use adsb.lol. OpenAQ reuse is dataset-specific,
and Global Fishing Watch account eligibility must be established before signup.

Status: source catalogue with dated verification. The original research was checked against official documentation on 2 September 2026; unconfirmed claims are marked UNVERIFIED. Section O records probes from this host. Section P records the implemented Phase 5 scope and its remaining limitations as of 6 September 2026. Section Q records the active automated-research implementation. Older catalogue rows describe candidate capabilities, not a promise that every connector exists.

Conventions:

- **Auth**: none / free key / free account / paid.
- **Reliability default**: the registry uses separate A-F source reliability and 1-6 item credibility. Earlier rows are catalogue-era expectations; exact current grades and their inherited editorial basis live in the registry and authenticated `/sources` view. Instrument/platform categories do not confer a universal grade. New research publisher/account items are explicitly unassessed. See section Q and `03_DOCTRINE_AND_REPORTING.md` section 4.
- **Phase**: when the connector is planned (see `05_ROADMAP.md`). "Could" means possible later, "Skip" means rejected with the reason given.
- Every connector is polite: conditional requests, descriptive User-Agent with contact address, caching at or above the upstream refresh interval, and a circuit breaker.

Headline changes discovered during research: UCDP now requires an access token; ReliefWeb requires a pre-approved application name; ACLED grants event-level data by email domain (a Gmail address gets the aggregated "Open myACLED" tier); the OFSI consolidated list closed in January 2026 in favour of the single UK Sanctions List; REST Countries now needs a key; Metaculus needs a token even to read; X/Twitter has no free tier; DeepStateMap keys are by permission; ProMED is paywalled (the WHO Disease Outbreak News endpoint is the free substitute); the Bellingcat Ukraine TimeMap wound down in February 2026 and is now an archive.

## A. Aviation

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| OpenSky Network REST | Global state vectors (`/states/all`), flights by aircraft or airport, tracks | Free account, OAuth2 client credentials (Basic auth deprecated); anonymous still works | Daily credits: anonymous 400, registered 4,000, feeder 8,000. A global `/states/all` costs 4 credits, so a registered account gets roughly one global poll every 90 s | 5 s (auth) or 10 s (anon) resolution | Yes, plus altitude, velocity, track, squawk, position source, category | Research and hobby use accepted | A | 1 | The baseline global picture. Regional bounding boxes cost 1 to 3 credits, so poll AOIs more often than the globe |
| adsb.lol | Community ADS-B, ADSBx v2 API family: `/v2/mil`, `/v2/ladd`, `/v2/pia`, `/v2/point/{lat}/{lon}/{radius<=250nm}`, `/v2/closest`, `/v2/hex`, `/v2/callsign`, `/v2/sqk`; route lookup | None (feeder keys planned) | Dynamic; back off on 4xx | Live | Yes | ODbL 1.0 (attribution and share-alike on derived databases) | A | 1 | Primary community source: military list plus radius queries over AOIs. Fields include `nac_p`, `nic`, `emergency`, `dbFlags` (1 military, 2 interesting, 4 PIA, 8 LADD) |
| airplanes.live | Same v2 API family | None | About 1 request/s (UNVERIFIED: the docs page blocked the fetch) | Live | Yes | Terms UNVERIFIED | A | 1 | Same connector class as adsb.lol with a different base URL; used as the second opinion and fallback |
| adsb.fi | `/v2/{hex,callsign,registration,sqk,mil}`, `/v3/lat/lon/dist` | None | 1 request/s; bad requests earn temporary IP bans | Live | Yes | Personal, non-commercial; must cite with link | A | 3 | Fallback only |
| ADS-B Exchange | Community API | Paid (RapidAPI, from 10 USD/month) | | | | Non-commercial community terms | | Skip | Confirmed no free tier |
| tar1090-db (Mictronics data) | Hex to registration, type, military/interesting/PIA/LADD flags, operator | None (GitHub raw `aircraft.csv.gz`) | | Periodic | | Licence UNVERIFIED (no LICENSE file) | | 3 | Enriches every aircraft; refresh weekly |
| GNSS interference (own layer) | Hourly H3 map of likely GPS jamming | Derived | | Hourly | H3 cells | Our own derivation | | 3 | Replicates the published GPSJam method: bin aircraft by H3 cell over 24 h, count low `nac_p` as bad, `percent_bad = 100*(bad-1)/(good+bad)`, green under 2 percent, amber 2 to 10, red above 10 |
| FAA NOTAM API | Global NOTAMs (GeoJSON, AIXM) | OAuth2 credentials granted by emailing the FAA | UNVERIFIED | Live | Yes | Gated | | Defer | Not self-serve; a later experiment |
| Aviation Safety Network | Accident database | Web only | | | No | Blocks bots, no RSS found | | Skip | |

## B. Maritime

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| AISStream.io | WebSocket AIS: subscribe by bounding boxes and optional MMSI list; 25 message types incl. PositionReport, ShipStaticData | Free key (GitHub sign-in) | 3 subscriptions per account, 3 connections per IP; subscribe within 3 s; slow consumers are dropped | Real time | Yes | No published data licence, no SLA (redistribution terms UNVERIFIED) | A | 3 | Terrestrial receivers only, so open ocean is dark. Browser connections forbidden: the backend consumes and fans out over SSE. One subscription covers all chokepoint boxes |
| AISHub | Aggregated AIS web service | Free account but you must feed your own receiver | 1 request/min | 1 min | Yes | Members only | | Skip unless Alex runs a receiver | |
| Global Fishing Watch API v3 | Vessels, events (FISHING, ENCOUNTER, LOITERING, PORT_VISIT, GAP), 4Wings tiles, insights | Free token | 50,000 requests/day, 1.5M/month | Hours to days behind real time | Yes | CC BY-NC 4.0, attribute "Powered by Global Fishing Watch" | B | 3 | "Going dark" (AIS gap) and loitering events are the OSINT value |
| NGA Maritime Safety Information | NAVAREA and HYDROARC broadcast warnings (`/api/publications/broadcast-warn`), anti-shipping activity messages (ASAM) | None | None stated | As issued | Broadcast warnings: positions in free text; ASAM: lat/lon | US Government work | A | 3 | Server intermittently 503/404; ASAM path UNVERIFIED (community code uses `/api/publications/asam`). Positions in warnings need a coordinate parser |
| UKMTO / IMB Piracy Reporting Centre | Advisories, live piracy map | None | | | IMB map plots positions | HTML only, copyright pages | | Skip | Use NGA ASAM instead; link out to UKMTO |

## C. Space

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| CelesTrak GP | Orbital elements by group (`active`, `stations`, `military`, `gnss`, `starlink`, `last-30-days` and more) as TLE, OMM JSON or CSV | None | Data refreshes every 2 h; re-requesting a group early returns 403; heavy error rates or over 100 MB/day get the IP blocked | 2 h | Elements only; propagate with SGP4 (satellite.js in the browser) | Free under usage policy | A | 3 | Cache each group for at least 2 h; stop immediately on 301/403/404 |
| Space-Track.org | GP, SATCAT, decay, conjunction messages | Free account | Under 30 requests/min and 300/h; GP hourly | Hourly | Elements | No redistribution without approval | A | Defer | CelesTrak is enough for a hobby app |
| N2YO | Positions, passes, satellites above a point | Free key | 1,000/h positions, 100/h passes | Live | Yes | Single key per user | A | Could | Requires NORAD IDs since July 2026 |
| Launch Library 2 (The Space Devs) | Launches, events, pads | None | 15 requests/h on the free tier | On update | Pads have lat/lon | Free | B | 3 | Poll the upcoming list at most every 10 min |
| NOAA SWPC | Alerts, planetary K index and forecast, NOAA scales, solar regions, aurora oval | None | None stated | Minutes | Aurora grid | US public domain | A | 1 | Directory listings only, no schema docs |

## D. Natural disasters and environment

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| NASA FIRMS | Active fire hotspots by area or world for VIIRS (SNPP, NOAA-20, NOAA-21), MODIS, Landsat, in NRT and standard processing | Free MAP_KEY | 5,000 transactions per 10 min; large date ranges count as several | NRT about 3 h; ultra-real-time under 60 s for much of North America | Yes | NASA open data, cite FIRMS | A | 1 | CSV output; maximum 5 days per query; the country endpoint is currently unavailable. Fire radiative power drives the severity scale |
| NASA EONET v3 | Curated natural events in 13 categories with source links and GeoJSON | None | None stated | Curated, lags hours to days | Yes | NASA open | A | 1 | Good for volcano, storm and iceberg tracks with history |
| GDACS | Multi-hazard alerts (earthquake, cyclone, flood, volcano, drought, wildfire, tsunami) with alert level, severity, population exposed; RSS and a GeoJSON API with date and type filters | None | None stated | Near real time | Yes, with bounding boxes | RSS declares public domain; JRC terms of use (March 2025) | A | 1 | The backbone of the disaster tracker |
| USGS Earthquakes | GeoJSON summary feeds (significant, M4.5+, M2.5+, all) by hour/day/week/month; FDSN event query for history | None | Feeds update every minute; FDSN returns up to 20,000 events | 1 min | Yes, with depth | US public domain | A | 1 | Track the `updated` field: magnitudes are revised |
| EMSC (seismicportal.eu) | Real-time WebSocket of new and updated events; FDSN query | None | Ping every 15 s | Seconds | Yes | CC BY 4.0 | A | 1 | Faster than USGS outside the US; needs reconnect logic |
| NOAA NWS alerts | Active US warnings (`/alerts/active`) by area, point or zone | None, but a User-Agent with app name and contact is mandatory | Undisclosed; retry after about 5 s | As issued | Many alerts lack polygons; resolve zone geometry separately | US public domain | A | 3 | |
| NHC and JTWC | Atlantic/Pacific advisories with cone, track and wind radii GIS products; JTWC RSS with warning text and KMZ | None | Poll hourly | Per advisory (6-hourly) | In GIS/KMZ products | US public domain | A | 3 | JTWC HTML blocks bots; the RSS and KMZ fetch fine |
| Copernicus EMS Rapid Mapping | Public activations with AOI polygons and product links | None | None stated | Per activation | Yes | CC BY 4.0, attribute Copernicus EMS | A | 3 | Portal moved in 2026; the dashboard API is the stable entry point |
| MeteoAlarm | European weather warnings per country as Atom/CAP; EDR API with GeoJSON | None for Atom | None stated | As issued | Region codes; polygons via EDR | CC BY 4.0 with mandatory credit and issue time; redistribute the original unmodified alongside any changes | A | 3 | Legacy RSS was retired January 2026; use the Atom feeds |
| Smithsonian Global Volcanism Program | Weekly volcanic activity report (RSS, CAP, KML) and a WFS with volcano locations | None | None stated | Weekly (Wednesday) | KML/WFS carry lat/lon; RSS does not | Smithsonian, cite | A | 3 | Site blocks bots; URLs UNVERIFIED by direct fetch |
| NOAA tsunami (NTWC/PTWC) | Atom and CAP feeds per centre | None | | Per event | CAP details; coordinates UNVERIFIED | US public domain | A | 3 | Usually empty, which is the point |
| UK Met Office DataHub | Site-specific forecasts (360 calls/day free); severe weather warnings via NSWWS public API by request; legacy warnings RSS still valid | Free account, `apikey` header | Daily limits reset 00:00 UTC | Hourly | Yes | Met Office terms | A | Could | DataPoint is retired; NSWWS keys are not self-serve |
| Open-Meteo | Forecast, current conditions, air quality, marine | None | Under 10,000/day, 5,000/h, 600/min | Hourly | Point queries | CC BY 4.0, non-commercial free tier | A | 3 | Weather context for assessments (cloud cover, wind) |
| RainViewer | Past radar tiles (2 h history, zoom capped at 7) | None | 100 requests per IP per minute | 10 min | Tiles | Personal or educational only; attribution link | | Could | Product shrank sharply at the end of 2025; treat as optional overlay |
| OpenAQ v3 | Air quality locations, latest, measurements | Free key | 60/min, 2,000/h | Varies | Yes | CC BY 4.0 (per provider) | A | Could | |
| WAQI | Air quality by geo, bounds, search | Free token | 1,000/s nominal | Hourly | Yes | Forbids caching, archiving and redistribution | | Skip | Incompatible with a fusion cache |
| EURDEP | European gamma dose rates | None (map only) | | Hourly | Yes | Data belongs to providers; no reuse without agreement | | Skip | Link out only |
| Safecast | Radiation measurements API and bulk CSV | None | None stated | Volunteer uploads | Yes | CC0 | C | Could | Mostly historical tracks, not live |
| IFRC GO | Appeals, events, field reports, flash updates, DREF | None for public data | None stated | As reported | Country level | Licence UNVERIFIED | B | 3 | Humanitarian response context for SITREPs |
| NASA GIBS (imagery) | WMTS tiles: daily VIIRS/MODIS true colour, GOES GeoColor (10 min), IMERG precipitation, cloud top height, VIIRS night lights | None | None stated | 10 min to daily | Tiles | NASA open | | 1 | Base layer and overlay source; verify layer IDs against `WMTSCapabilities.xml` |

## E. Base maps, imagery and terrain

| Source | What | Auth | Limits | Licence note | Phase | Notes |
|---|---|---|---|---|---|---|
| OpenFreeMap | Vector tile styles (`dark`, `positron`, `bright`, `liberty`, `fiord`, `3d`) | None | None; commercial use allowed | Attribution "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" | 1 | Default dark globe and map style |
| Ordnance Survey OS Maps API | ZXY raster tiles `Road_3857`, `Outdoor_3857`, `Light_3857` (zoom 7 to 16 free; 17 to 20 premium); Leisure only in EPSG:27700 | Free OpenData plan key | 600 transactions per minute per API per project; HTTP 429 beyond | "Contains OS data © Crown copyright and database rights [year]" plus the OS logo; Great Britain only | 1 | Proxied through the API with a tile cache so the key stays server-side. OS Vector Tile API (Open Zoomstack) is also free but reaches end of life in autumn 2028 |
| EOX Sentinel-2 cloudless | Annual global cloud-free mosaics (2016, 2018 to 2025) as WMTS/XYZ | None | None stated | 2016 CC BY 4.0; 2018 onward CC BY-NC-SA 4.0 with the EOX attribution line | 1 | Default satellite base |
| NASA GIBS | Daily VIIRS true colour, VIIRS day/night band (night lights), static Black Marble, GOES GeoColor, precipitation and cloud layers as WMTS | None | None stated | NASA open data; acknowledgement sentence requested | 1 | Date-driven satellite view: "what did this look like yesterday"; night lights reveal power outages |
| Esri World Imagery | Global high-resolution mosaic tiles | None | No systematic harvesting | Non-commercial use with attribution permitted; Esri is retiring legacy raster basemaps in phases from October 2026 (scope UNVERIFIED) | Optional | Offered as a switchable alternative, not the default |
| Protomaps | Vector basemap with `labelsOnly` flavour for the hybrid view; planet PMTiles for self-hosting (about 120 GB) or hosted API | Free key for the hosted API | About 1M tiles per month, non-commercial | "Protomaps © OpenStreetMap" | 1 | Hybrid = satellite plus labels; self-hosting a regional extract is an option |
| CARTO basemaps | `dark-matter` vector style | None today | 5M tiles per month fair use | © OpenStreetMap © CARTO | Fallback | Only if OpenFreeMap is unavailable |
| Mapterhorn / AWS Terrain Tiles | Terrarium-encoded DEM tiles for MapLibre terrain | None | Fair use (Mapterhorn hosted terms UNVERIFIED) | Attribution list required | 6 | Optional 3D terrain in map mode |

## F. News

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| GDELT GEO 2.0 API | Geolocated news as GeoJSON points or heat maps, with country and ADM1 modes | None | None published; default last 24 h, maximum 7 days, up to 1,000 points per call | 15 min | Yes | Free for any use; cite and link gdeltproject.org | Inherits outlet where known, else C | 1 | The natural globe news feed: 65 languages already geolocated |
| GDELT DOC 2.0 API | Article search across 65 machine-translated languages with `sourcelang:`, `sourcecountry:`, `theme:`, tone filters; article list, volume timeline and tone chart modes | None | None published; be gentle (429s reported, UNVERIFIED); 250 records per call; history to 2017 | 15 min | Source country only | As above | Inherits, else C | 1 | Country panels (volume and tone sparklines), evidence search for reports |
| GDELT 2.0 raw 15-minute files | Events (CAMEO codes, actors, Goldstein scale, lat/lon), Mentions, Global Knowledge Graph | None | None stated; today's batch: Events 75 KB, Mentions 135 KB, GKG 6.4 MB zipped | 15 min | Yes | As above | C | 2 | Use Events only (conflict CAMEO codes 18 to 20 are the real-time conflict signal); GKG is about 600 MB/day and is skipped |
| GDELT Web NGrams 3.0 | Per-minute snippets in 152 languages | None | Firehose scale | 1 min | No | As above | | Skip | Too heavy for the design |
| Google News RSS | Keyword-search feeds per edition (`hl`, `gl`, `ceid`), with `when:1d` queries | None | Upstream limits undocumented; local collector caps at 12 terms and 48 requests/hour | At least 15 minutes per term | No location supplied by the search query | Google terms; publisher rights apply | C, aggregator independence unverified | 5, built | Enabled collection plans drive literal phrase searches in the GB English edition. Legacy embedded publisher URLs are decoded only for cited evidence. Modern opaque links remain original Google URLs; see section P |
| Outlet RSS bundle (verified live today) | Al Jazeera English and Arabic, France 24 (EN; FR and AR UNVERIFIED), Kyiv Independent, Ukrainska Pravda (UK and EN), Meduza (EN and RU), TASS (EN), RIA and Sputnik, Xinhua (HTTP only), Global Times (stale), CNA Focus Taiwan, Times of Israel, Haaretz, Anadolu, Dawn, Nikkei Asia, Crisis Group CrisisWatch | None | Per outlet | Continuous | No; geoparsed by us | Personal use terms vary | B for wire and public broadcasters, C for national press, C with `state_controlled` for TASS, RIA, Sputnik, Xinhua, Global Times | 1 | Seeded as registry rows, not code |
| Outlet RSS (blocked from this environment, UNVERIFIED) | BBC, DW (30 languages), NHK World, Yonhap, The Hindu, Le Monde (FR and EN), El País, Folha, Kremlin.ru (EN), ISW | None | | | | | B or C | 1 | Feed URLs are known; verify on first run |
| Reuters and AP | Original research found no official RSS | | | | | | B when the source is established | Candidate coverage through aggregators | Reuters also has an implemented outlet YouTube feed. Google News watchlist items currently remain aggregator C; URL decoding does not automatically assign an outlet grade |
| Wikipedia Current events portal | Daily bullet list via the Action API (`action=parse`) | None | | Daily | No | CC BY-SA | B | 2 | Parsed to a small daily digest |
| Wikimedia EventStreams | SSE of recent changes across wikis | None; User-Agent required | Small-scale tools; 15-minute connection timeout, resume with `Last-Event-ID` | Real time | No | CC BY-SA | | 4 | Edit bursts on country or conflict pages as an attention indicator |
| Wikimedia Pageviews REST | Per-article and top views | None | 10 requests/min unidentified, 200/min with a proper User-Agent | Daily with about a day of lag | No | CC0 (UNVERIFIED) | | 4 | Attention spikes per country and conflict page |
| Wikidata SPARQL | Entity lookups with coordinates | None; User-Agent mandatory | 60 s timeout; 5 parallel per IP; 30 errors/min | Live | Yes | CC0 | | 2 | Country facts and infrastructure reference |

## G. Conflict

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| UCDP GED and Candidate events | Georeferenced conflict events with deaths; GED is annual, Candidate events monthly | Access token required (`x-ucdp-access-token`, requested from the maintainers) | 5,000 requests/day; paged JSON | Monthly | Yes | Free for academic and non-commercial use; cite | B | 3 | The dependable event dataset for trends |
| ACLED | Events with type, actors, fatalities, coordinates | Free myACLED account with OAuth (24 h access token, 14 day refresh) | 5,000 rows per request; tier quotas UNVERIFIED | Weekly | Yes | Terms of use, attribution, non-commercial, no raw redistribution | B | 3 | Access is tiered by email domain: a Gmail address gets "Open myACLED" (aggregated data, Explorer, CAST); institutional email gets event-level data. Old API keys ended September 2025 |
| GDELT Events (CAMEO 18 to 20) | Real-time coded conflict events | None | See section F | 15 min | Yes | GDELT terms | C | 2 | Noisy but immediate; corroboration engine handles the noise |
| ISW / Critical Threats ArcGIS services | Ukraine assessed control of terrain, assessed advances, 24-hour gains as public feature layers | None | ArcGIS defaults (2,000 features per query, paginate) | Daily | Polygons | No licence in item metadata; attribute ISW/CTP (redistribution UNVERIFIED) | B | 3 | Query with `f=geojson`; proxied and cached daily |
| Bellingcat Ukraine TimeMap | Civilian harm incidents February 2022 to December 2025 | None | | Project wound down February 2026 | Yes | Data licence not stated (UNVERIFIED); code under a Do No Harm licence | B | 3 | One-off archive import for the Ukraine tracker |
| alerts.in.ua | Ukraine air-raid alerts by oblast, raion and hromada | Free token via form | Soft 8 to 10 requests/min, hard 12/min per IP | Real time | Region identifiers; polygons from geoBoundaries ADM1 | "Not for critical infrastructure" | A | 3 | ukrainealarm.com is the alternative (key via form) |
| Israel Home Front Command (Pikud HaOref) | Siren alerts by area | None, but geo-blocked to Israeli IPs and requires specific headers | Unofficial | Real time | Area names | Unofficial | A | Could | Needs an Israeli proxy; off by default |
| Taiwan MND daily PLA activity | Aircraft and ship counts, ADIZ incursions | None | | Daily about 09:00 Taipei | Maps in images only | Government copyright | B | 3 | Import the community-maintained CSIS ChinaPower ADIZ dataset rather than scrape |
| Japan MOD Joint Staff releases | Foreign naval and air activity around Japan | None | | Ad hoc | Maps in PDFs | Government | B | Defer | No RSS found (UNVERIFIED); PDFs only |
| HDX HAPI | Aggregated conflict events by admin area, plus food security, refugees, IDPs, needs, population | Free `app_identifier` (encoded name and email) | 10,000 rows per page | Varies | Admin p-codes, no coordinates | HDX HAPI terms | B | 3 | Aggregated conflict counts even where ACLED event-level access is unavailable |
| DeepStateMap | Ukraine front line polygons | Key by permission (humanitarian and military use only) | | Daily | Yes | Permission required | | Skip unless permission is granted | An unauthenticated history endpoint responds but must not be used without asking |
| Airwars | Strike and casualty archive | | | | | No API or bulk download (UNVERIFIED) | | Skip | Link out |
| Liveuamap | Events | Paid (from 150 USD/month) | | | | Commercial | | Skip | Confirmed no free API |
| CFR Global Conflict Tracker, HIIK Conflict Barometer | Conflict profiles; annual datasets | None | | Monthly; annual | Country | Copyright; cite | B | Reference | Seed the conflict list and link out |

## H. Social

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Bluesky public AppView | `searchPosts`, author feeds, custom feeds | None | 3,000 requests per 5 min per IP | Real time | No | Bluesky terms; users own content | E (named OSINT accounts may be raised) | Deferred | Repeated 403 responses from this host on 5 September 2026. No connector is enabled |
| Bluesky Jetstream | Full-network JSON firehose filtered by collection | None | Up to 100 collections and 10,000 DIDs per subscription | Real time | No | As above | E | Could | Only worth it with server-side keyword filtering |
| Mastodon | Hashtag timelines per configured instance | None unless the instance disables public preview | 40 items per hashtag request; polling every 15 to 30 minutes by instance | Feed publication | No coordinates supplied by this connector | Per-instance rules | E, credibility 6 until graded | 5, built | Four reviewed instances and 16 hashtags packaged in `backend/src/ase/resources/social_watch.json`, verified 16 September 2026 (see [SOCIAL_SOURCE_COVERAGE.md](SOCIAL_SOURCE_COVERAGE.md)); HTML is reduced to text |
| Reddit RSS | Subreddit Atom listings | None | Upstream may return 429; polls every 15 or 30 minutes by source, paced 5 s apart per host | Feed publication | No | Reddit terms; descriptive User-Agent | E, credibility 6 until graded | 5, built | `worldnews`, `geopolitics` and `UkrainianConflict`; no OAuth or article scraping. Not widened: `robots.txt` disallows every path for every user agent (16 September 2026) |
| YouTube channel RSS | Latest outlet video titles and links | None | Local polling every 30 minutes | Feed publication | No | YouTube terms | B/C inherited from the named outlet | 5, built | BBC, Reuters, DW, Al Jazeera, France 24 and Sky; no video download or Data API. Not widened: `robots.txt` disallows `/feeds/videos.xml` (16 September 2026) |
| Telegram | Public channel web previews at `t.me/s/<channel>` for 63 curated channels | None | One page per channel; at most 20 posts and a 700-character excerpt each; 30 to 240 minute polling, 5-second per-host pacing, about 57 requests per hour | Post publication | No coordinates supplied by this connector | Telegram terms; text excerpts, timestamps and post links only; no media and no account | E, credibility 6 for every channel including official ones | Built, 16 September 2026 | Reverses open question 7 at the operator's explicit request. Bounded `html.parser` route that refuses rather than improvises; a markup change defers with a stated reason. Registry, rejections and gaps in [TELEGRAM_CHANNEL_COVERAGE.md](TELEGRAM_CHANNEL_COVERAGE.md) |
| VK | Public group walls | Service token (phone-verified account) | About 3 requests/s (UNVERIFIED) | Live | No | VK terms, Russian jurisdiction | E | Skip | |
| X / Twitter | Posts | Pay-per-use only since February 2026 (0.005 USD per read) | | | | Commercial | | Skip | No free tier |

## I. Cyber

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| CISA Known Exploited Vulnerabilities | JSON catalogue with schema; advisories RSS | None | None | Near daily | No | CC0 | A | 3 | |
| NVD API 2.0 | CVE detail | Optional free key | 5 requests per 30 s without key, 50 with | Continuous | No | US public domain | A | 3 | Enrichment only |
| ransomware.live v2 | Victims by country and group | None (PRO tier has a free key) | 1 request/min per endpoint | Continuous | ISO country code (geocoded, noisy) | Personal use only; attribute | B for the aggregator; victim claims are criminal statements, so credibility starts at 3 | 3 | Country panel and cyber map |
| Cloudflare Radar | Internet outages and annotations, traffic anomalies by country or ASN | Free account and token (Radar read) | 1,200 requests per 5 min | Near real time | ISO country, ASN | Radar data CC BY-NC 4.0 (UNVERIFIED) | B | 3 | |
| IODA (Georgia Tech) | Outage summaries, alerts, events and raw signals per country, region or ASN | None | Unpublished | Near real time | Country and region codes | Academic; attribute | B | 3 | Internet shutdown indicator on the globe |
| CTI publisher RSS (NCSC, CISA, CERT-UA, CCCS, CERT-FR, IC3, CERT-EU, ACSC, Microsoft, Talos, Google/Mandiant, Unit 42, SANS ISC) | Headline-only threat reports and advisories | None | Polite polling every 30 min | Continuous | No (publisher location discarded) | Publisher terms; headlines and links only | F6 unassessed; official issuers flagged | Cyber workspace | See `CYBER_THREAT_INTELLIGENCE.md` |
| Specialist cyber news RSS (The Record, BleepingComputer) | Headline-only news, `news_report` kind | None | Polite polling every 30 min | Continuous | No | Outlet terms; headlines and links only | F6 unassessed | Cyber workspace | Journalism never counted as research |
| abuse.ch (URLhaus, ThreatFox, Feodo) | Indicators of compromise | Free Auth-Key required since 2025 | Fair use | Continuous | No | CC0 (UNVERIFIED) | A | Could | Not needed for the globe |
| AlienVault OTX | Pulses and indicators | Free key | 10,000 requests/h | Continuous | No | OTX terms | C | Could | |

## J. Government and political

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| GOV.UK Content API | FCDO travel advice per country (`alert_status`, parts, change history) | None | 10 requests/s | On change | Country slug | OGL v3 | A | 1 | Country panel risk level |
| GOV.UK Atom feeds | News by organisation or topic (FCDO, MOD, Home Office and others) | None | 10 requests/s | Continuous | No | OGL v3 | B (`interested_party` for MOD claims about adversaries) | 1 | |
| US State Department travel advisories | Level per country | None | | On change | Country | US Government | A | 1 | RSS verified |
| White House, DoD, CENTCOM, State Department press | Releases | None | | Daily | No | US Government | B (`interested_party`) | 3 | State Department feed returned 403 to bots (UNVERIFIED) |
| UN press and UN News | Meetings coverage including the Security Council; news | None | | Daily | No | UN terms | B | 1 | RSS verified |
| NATO news, EU Council press | Releases | None | | Daily | No | | B | Defer | Feed URLs UNVERIFIED after site redesigns |
| Kremlin.ru (English) | Presidential events and statements | None | | Daily | No | | C (`state_controlled`) | 3 | Feed UNVERIFIED |

## K. Humanitarian and health

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| ReliefWeb API v2 | Reports, disasters (GLIDE numbers), countries | Pre-approved `appname` required since November 2025 | 1,000 calls/day; 1,000 results per query | Continuous | ISO3 and primary country | Site CC BY 4.0; reports keep source copyright | B | 1 once approved | |
| WHO Disease Outbreak News | Outbreak notices | None | Unpublished | Weekly or so | Country in title only | WHO terms | A | 3 | The documented RSS is gone; the OData endpoint works (verified) |
| ProMED | Outbreak posts | Subscription since April 2026 | | | | Paywalled | | Skip | WHO DON is the substitute |
| IFRC GO | See section D | | | | | | B | 3 | |
| HDX HAPI | See section G | | | | | | B | 3 | |
| UNHCR Refugee Statistics API | Population and asylum figures | None | Unpublished | Annual and mid-year | Country | UNHCR terms | A | Could | |
| IOM DTM API v3 | IDP figures by admin level | Free developer portal account and subscription key | Unpublished | Context dependent | Admin levels | Citation required | A | Could | |
| ACAPS | INFORM Severity index, crisis datasets | Free account token | Unpublished | Monthly | Country and crisis | Free, cite | B | Could | |
| FEWS NET FDW | IPC food security phases as GeoJSON, prices | None for public data | Unpublished | Periodic | Admin units | Data usage policy | A | Could | |

## L. Economic, sanctions and forecasting

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Reliability | Phase | Notes |
|---|---|---|---|---|---|---|---|---|---|
| OFAC sanctions lists | SDN and consolidated lists as XML/CSV | None | | On designation | Country fields | US Government | A | 3 | RSS retired January 2025; poll the export files |
| UK Sanctions List | Single UK source since 28 January 2026 (the OFSI consolidated list closed) | None | | On designation | Country fields | OGL | A | 3 | XML export |
| EU consolidated sanctions list | XML/CSV | Public token in the URL | | On designation | Country fields | EU reuse | A | 3 | |
| OpenSanctions | Merged sanctions and PEP graph | Bulk: none; API: paid or free on application | | Daily | Country codes | Bulk data CC BY-NC 4.0 | A | Could | Bulk download only |
| Polymarket Gamma API | Events, markets, prices | None for reads | Soft per-IP (UNVERIFIED) | Real time | No | Polymarket terms | Signal, not a report | 4 | Indicator inputs ("probability of X above 30 percent") |
| Metaculus | Forecast questions | Token required even to read | Unpublished | Live | No | Metaculus terms | Signal | Could | |
| Manifold | Markets | None for reads | 500 requests/min per IP | Live | No | No commercial AI training | Signal | Could | |
| FRED, EIA, World Bank, CoinGecko | Macro, energy, development indicators, crypto prices | Free keys (World Bank none) | 120/min; 9,000/h; unpublished; 30/min | Daily to annual | Country | Attribution | A | Could | Context for country briefs |

## M. Reference, geocoding and archiving

| Source | What | Auth | Limits | Cadence | Geo | Licence note | Phase | Notes |
|---|---|---|---|---|---|---|---|---|
| GeoNames dumps | `cities500` to `cities15000`, `allCountries`, `countryInfo.txt`, daily modification files | None | None | Daily | Yes | CC BY 4.0 | 1 | The offline gazetteer behind our own geoparser (spaCy small NER plus a GeoNames matcher); the web services (10,000 credits/day) are not needed |
| Natural Earth | Admin-0 and admin-1 boundaries, populated places | None | None | Irregular | Yes | Public domain | 1 | Country polygons for the nation filter and choropleths |
| geoBoundaries | ADM0 to ADM2 boundaries per country | None | None | Releases | Yes | gbOpen CC BY 4.0 with attribution link | 3 | Oblast polygons for air-raid alerts and admin-level aggregates |
| Wikidata | Country facts, infrastructure, coordinates | None | See section F | Live | Yes | CC0 | 2 | Replaces REST Countries, which now needs a key with 500 requests/month |
| Nominatim (OSM) | Geocoding | None; valid User-Agent mandatory | 1 request/s; no bulk; cache results | Live | Yes | ODbL | Could | Only for admin-entered AOI search; Photon self-host if volume grows |
| Overpass API | OSM features (military bases, airports, ports, power plants) | None; User-Agent required | Fair use, no parallel queries, frequently overloaded | Live | Yes | ODbL | 3 | On-demand infrastructure layer per AOI with long caching |
| Internet Archive Wayback Availability API | Nearest existing snapshot for a URL | None | Unpublished | Live | No | IA terms | 2 | Check before saving |
| Internet Archive Save Page Now 2 | Archive a URL on demand, job id and status | S3-style keys from the IA account | Concurrency limited; community clients stay around 15 requests/min (official numbers UNVERIFIED) | Live | No | IA terms | 2 | Evidence preservation for cited URLs; many domains are blocklisted, so failures are recorded, not retried forever |
| archive.today | Manual snapshots | None | CAPTCHA on scripted use | | | Unofficial | Skip | ArchiveBox self-hosting is the later option |

## N. Python libraries (maintenance check)

| Library | Status | Use |
|---|---|---|
| feedparser 6.0.14 (July 2026) | Active, BSD | RSS and Atom parsing behind `defusedxml` |
| trafilatura 2.x | Active, Apache 2.0 | Article text extraction for top evidence items |
| py3langid 0.4.0 | Active, pure Python, 4.5 MB installed, 97 languages restricted to the 24 the feeds carry | Language detection on short titles. lingua-language-detector was tried first and dropped because its wheel installs 291 MB of models, out of proportion for a home machine |
| fasttext | Upstream archived March 2024 | Avoid |
| mordecai3 | Dormant pre-release, needs Elasticsearch | Avoid; build a small spaCy NER plus GeoNames matcher instead |

## O. Live verification, 5 September 2026

Every row was fetched from the development host with the project's User-Agent on 5 September 2026. Where this section disagrees with a row above, this section wins.

| Source | What was fetched | Result | Consequence |
|---|---|---|---|
| adsb.lol | `/v2/mil`, `/v2/ladd`, `/v2/pia`, `/v2/sqk/7700`, `/v2/point/51.5/-0.1/100` | All 200; aircraft carry `nac_p`, `nic`, `emergency`, `dbFlags`, `squawk`, `category` | Military, interesting, LADD, PIA, emergency and area-of-interest civil traffic all work without a key; the GNSS interference map has its inputs |
| adsb.fi | `/api/v2/mil` | 200 | Fallback for the military list |
| OpenSky | anonymous `/states/all` with a UK bounding box | 200 (63 KB) | Area-of-interest civil traffic without an account, within the 400 daily credits |
| NGA MSI | `broadcast-warn?status=active` | 200, 386 warnings, positions in free text | NAVAREA warnings need a coordinate parser ("19-23.0N 092-03.1W") |
| NGA MSI | `asam` with every documented parameter set | 404 | Anti-shipping messages unavailable; UKMTO stays a link-out |
| CelesTrak | `gp.php?GROUP=stations&FORMAT=json` | 200 | Satellite propagation with SGP4 |
| Launch Library 2 | `launches/upcoming` | 200 | Launch schedule; 15 calls an hour |
| SWPC | `ovation_aurora_latest.json`, `noaa-planetary-k-index.json` | 200, 200 | Aurora oval and K index |
| EMSC | FDSN `event/1/query?format=json` | 200 | Fast earthquakes outside the US |
| NHC | `index-at.xml`, `index-ep.xml` | 200 with `nhc:Cyclone` elements (centre, type, name, wind, pressure, movement) | Cyclone connector, Atlantic and East Pacific |
| JTWC | `rss/jtwc.rss` and a warning text | 200; warning text carries "NEAR 26.2N 127.5E" and forecast positions | Cyclone connector, West Pacific and Indian Ocean |
| Smithsonian GVP | `WeeklyVolcanoRSS.xml` | 200 with `georss:point` per item | Weekly volcano connector; the catalogue's "no coordinates" note was wrong |
| NOAA tsunami | `PAAQAtom.xml`, `PHEBAtom.xml` | 200 with `geo:lat` and `geo:long` | Tsunami connector |
| NWS | `alerts/active?status=actual&message_type=alert&severity=Severe` | 200; `limit` is rejected; some alerts carry polygons | Severe weather connector for the US |
| Met Office | `WarningsRSS/Region/UK` | 200 (Atom, empty at the time) | UK warnings connector |
| MeteoAlarm | Europe-wide Atom paths; then `feeds/meteoalarm-legacy-atom-france` | Europe-wide 404; per-country Atom with CAP elements answers 200 | One connector per chosen country |
| Copernicus EMS | activations feed | No response | Deferred |
| NASA GIBS | VIIRS true colour, VIIRS day and night band, GOES-East GeoColor tiles | 200; IMERG precipitation layer id not confirmed | Imagery layers with a date picker |
| RainViewer | `weather-maps.json` | 200 | Optional radar overlay |
| ransomware.live | `v2/recentvictims` | 200 (100 victims with country and group) | Cyber tracker |
| IODA | `outages/alerts` | 200 | Outage alerts by country, region and network |
| NVD | `cves/2.0` | 200 | Enrichment only |
| URLhaus | `urls/recent` | 401 | Needs an auth key; not needed |
| Polymarket Gamma | `markets?active=true` | 200 | Indicator inputs |
| WHO Disease Outbreak News | OData with `$orderby=PublicationDate desc` | 200 | Outbreak connector (ordering is required; the default order starts in 2008) |
| HDX HAPI | `coordination-context/conflict-events` with an encoded app identifier | 200; filters `start_date`, `end_date`, `location_code`, `admin_level` | Monthly conflict aggregates by admin area; no registration needed |
| IFRC GO | `api/v2/event` | 200 | Humanitarian events for SITREPs |
| UNHCR | `population/v1/population` | 200 | Country context |
| FEWS NET | `api/ipcphase` | No response | Deferred |
| ReliefWeb | `v1/disasters?appname=allseeingeye` | 410 | Pre-approved application name still required |
| UK Sanctions List | GOV.UK content API lists XML, CSV, ODS and schema downloads at `sanctionslist.fcdo.gov.uk` | 200 | Sanctions context |
| OFAC | `sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML` | 200 (20 MB) | Sanctions context; the `RecentActions` path is 404 |
| UN press | `press.un.org/en/rss.xml` | 200 | Already seeded |
| CFR Global Conflict Tracker | RSS | 404 | Reference only, link out |
| Google News RSS | keyword search with `when:1d`, Ukrainian edition | 200 | Keyword collection for PIRs and foreign-language headlines |
| Bluesky public AppView | `searchPosts` with and without the User-Agent | 403 | Blocked from this host; re-checked at the start of Phase 5 on 5 September, still 403, so Bluesky stays out until a later probe answers |
| Mastodon | `mastodon.social`, `defcon.social`, `journa.host` and `eupolicy.social` hashtag timelines | 200; `robots.txt` allows the path | Social watchlists |
| Mastodon | `infosec.exchange`, `ioc.exchange`, `respublicae.eu` hashtag timelines | 422, unauthenticated API disabled | Refused, 16 September 2026 |
| Reddit | `r/worldnews/new/.rss` | 200 with the project's User-Agent, but `robots.txt` is `Disallow: /` for every user agent | Social watchlists without OAuth; not widened |
| YouTube | channel RSS | 200, but `robots.txt` disallows `/feeds/videos.xml` | Channel watchlists; not widened |
| Telegram | `t.me/s/<channel>` | 200 (HTML) | Now collected for 63 curated channels; `t.me/robots.txt` and `telegram.org/robots.txt` both 404, so no crawl rules are published |
| Kyiv Independent | `/feed/`, `/rss/` | 404 | Feed URL unknown |
| ISW | `/feed` | 200 but HTML, not a feed | No feed; ArcGIS search finds only historical control-of-terrain services |
| Focus Taiwan | `/rss/politics`, `/rss/all` | 404 | Taipei Times RSS answers instead |
| NHK | Japanese `rss/news/cat6.xml` | 200 | Japanese-language feed available; no English RSS |
| Critical Threats | `/feed` | 403 | Skip |
| ACLED | `api/acled/read` | 200 HTML (login page) | Account required, as catalogued |
| UCDP | `gedevents/25.1` | 401 | Token required, as catalogued |
| Overpass | small military airfield query | 200 | Infrastructure on demand |
| geoBoundaries | `gbOpen/UKR/ADM1` | 200 | Oblast polygons |
| Wikimedia | page views per article; current events portal parse | 200, 200 | Attention signals and a daily digest |
| GDELT DOC | `timelinetone` | 429 on the first call | Tone sparklines come from the live store, not from GDELT DOC |
| Open-Meteo | current conditions | 200 | Weather context |
| Wayback | availability API and Save Page Now | In use by the archiving job | Working since 5 September |

## P. Implemented social and keyword collection, 6 September 2026

The social board at `/trackers/social` reads the bounded live store. It shows the retained day's posts by platform and instance, top hashtags, the latest 50 posts and located-post counts. The existing social globe category displays events with a location; the Mastodon, Reddit and YouTube connectors do not invent coordinates. Public Mastodon/Reddit posts start at E6, while outlet YouTube channels retain their outlet reliability. Neither burst activity nor translation raises a source's grade.

Only the configured watchlist and enabled collection-plan keywords can acquire social baselines. The global cap is 32 normalised terms. Every five minutes the sampler updates the previous complete UTC hour, including zero counts, in `activity_samples`. It stores keyword digests and counts, prunes social history after 30 days and removes deselected keys. Private collection terms are shown only to their owner or an administrator. A burst requires at least six historical sampled hours, three posts and twice the historical mean. Unobserved hours remain gaps. Hashtags and raw posts are never written by this sampler.

Google News collection is a separate news feed, `google_news_watchlists`. It queries at most 12 deduplicated terms from enabled plans, at least one minute apart, with a 48-request rolling hourly cap and a 15-minute minimum per term. Searches are quoted literal phrases with `when:1d`, `hl=en-GB`, `gl=GB` and `ceid=GB:en`. Google receives those configured terms when collection is enabled. The source enters the normal news pipeline with aggregator reliability C; decoding a URL does not establish publisher independence or automatically change its grade.

The legacy Google News envelope can contain the publisher URL directly. That URL is decoded and checked for a public destination only after a report selects the item as cited evidence, within a 30-link, ten-second resolution budget. Uncited links and failed resolutions remain unchanged. No article HTML is fetched. A signature-free probe of the modern opaque-ID `batchexecute` path returned a null result with status 3 on 6 September 2026. Modern IDs therefore retain their original Google URL. Resolving them by extracting signatures from HTML would violate the feeds/APIs-only policy and is not implemented.

Language detection and optional model-backed title translation are documented in [Phase 5 and Phase 6 operations](PHASE5_PHASE6_OPERATIONS.md). The adapters have offline tests; translation, report generation and embeddings have not been verified against a configured real model on this host. The probe results above are dated observations, not continuing availability guarantees.

## Q. Active automated-research integration, 6 September 2026

This section describes implemented adapter contracts, not new live availability
probes. [The active plan](MASTER_AUTOMATED_RESEARCH_PLAN.md) records focused checks
and remaining integration/evaluation. The older host probes in section O retain
their original dates and must not be treated as current guarantees.

| Provider | Implemented bounded scope | Attribution and coverage limits |
| --- | --- | --- |
| Google News research RSS | Question terms and requested publication interval, one admitted request per configured edition; first 200 feed items considered | Undocumented feed; no article HTML, linked-page scraping or guaranteed completeness; terms are not automatically translated |
| Configured social RSS/Atom | Existing public feed seeds filtered by explicit terms and publication interval | Not arbitrary account discovery or full platform search; configured language is not independently verified; publisher/account metadata remains unverified |
| SEC submissions | Explicit CIK; at most 20 recent filing metadata records in the requested dates | Filing date has day precision; no full filing contents/older pagination; filing assertions are not SEC verification |
| SEC company directory | At most eight current name/ticker candidates | A candidate is not a confirmed intended identity or complete company register |
| Google Public DNS | Current resolver snapshot; quick mode requests A, detailed requests A/AAAA/MX/NS | No target-host connection or historical DNS; shared addresses/servers do not identify owners |
| Verisign RDAP | Explicit registered .com/.net domains, current registry metadata | No referral/contact crawl, registrable-domain guessing, beneficial ownership or historical-control proof |
| Companies House | Current profile by number or at most 20 name-match candidates, using an optional operator API key | No request when key is absent; UK registry coverage, no filed documents/officer/ownership investigation; prefer `GB:` or `companies-house:` prefixes to distinguish bare SEC CIK numbers |
| SSLMate certificate transparency | Optional authenticated exact-hostname query, first page of unexpired issuances, at most 20 retained records | No request without key; no wildcard/subdomain expansion or complete history; oldest discovered first, so not a latest-record guarantee; certificate validity is not observation or ownership |
| Supplied documents/media | Local isolated extraction with page/row/paragraph or frame locators | Not a new public source; original publication/capture claims may be unknown; OCR and metadata do not authenticate content |

The news edition map includes `en`, `fr`, `de`, `es`, `pt`, `uk`, `ru`, `ar`,
`zh-cn`, `zh-tw`, `ja`, `ko` and `hi`. This is request configuration, not proof of
translation quality, geographic relevance, Chinese-source access or balanced
coverage. Unsupported language/focus requests remain visible in receipts. No
Telegram preview scraping, paid API or additional cloud service is introduced.
SSLMate is a current certificate snapshot capability, not a full historical archive.

Private collection uses six requests/45 seconds/200 retained items in quick mode
and 24 requests/180 seconds/800 items in detailed mode. The additional challenge
pass shares six requests/45 seconds/200 items across judgements. These budgets
limit collection, not total model latency or the amount of available information.
Only selected report evidence and bounded receipts become durable; unselected
material is transient. Requests stay behind the existing guarded HTTP boundary.

### Source-rating transparency

`domain/source_rating_catalog.py` records the explicit basis of inherited registry
grades. `SourceRating` adds `ase-source-ratings-v1`, editorial/unassessed status,
assessed grade, scope, limitations, provenance role, whether publisher reliability
was assessed, and an optional review date. No historical review date, accuracy
percentage or fresh performance study is invented. The metadata does not silently
change grading or the per-judgement evidence policy.

Aggregators and social platforms do not transfer their own reputation to an
original publisher or account. Existing configured grades stay visible alongside
that limitation; unknown/new research items remain explicitly unassessed. A changed
configured grade without a matching recorded basis is not represented as a reviewed
rating. Separate organisation keys are declarations, not proven independent sourcing.

Selected evidence freezes this rating plus bounded scalar provenance such as
original publisher/account/source claims, identifiers, locator and timestamp hints.
The current `/sources` catalogue is authenticated and separate from historical
report snapshots. Legacy missing ratings remain unknown rather than being filled
from today's registry. Source links and hashes support traceability, not origin,
claim authenticity or a preserved copy of an entire original webpage.

`container/research_sources.py` registers every research edition/social source,
SEC, Companies House, DNS, RDAP, certificate and private document/media event ID.
All research catalogue entries are F/unassessed, with a source-specific basis and
limits. Unknown news/social/upload origins share empty organisation provenance;
separate editions or accounts therefore establish no extra known organisations.
Registry/resolver endpoints share their collector organisation. Disabled source IDs
and disabled parent feeds suppress their corresponding catalogue derivatives.
No API URLs or keys are returned by `/api/sources`; listing a capability does not
claim that credentials or local media tools are currently available.

### Official provider contracts checked on 6 September 2026

OpenAlex authentication rechecked on 11 September 2026: configure optional
`ASE_OPENALEX_API_KEY` in the backend environment. The server uses an origin-bound
Bearer header, disables redirects and keeps credentials out of URLs and shared
client state. Missing keys retain anonymous access; invalid configured credentials
fail without silently retrying anonymously. The research receipt identifies
authenticated or anonymous allowance. Existing explicit selection, publication
window and 20-record limit apply; the key does not enable full text or change
source reliability. See [OpenAlex authentication](https://help.openalex.org/api/authentication/).

Companies House requires API authentication and permits 600 requests per five
minutes. Its public data API is free; the implementation uses an operator key in
per-request credentials, not a shared client's global headers. See the official
[overview](https://developer.company-information.service.gov.uk/overview) and
[developer guidelines](https://developer.company-information.service.gov.uk/developer-guidelines/).
Configure `ASE_COMPANIES_HOUSE_KEY` separately; absence produces an unavailable receipt.

SSLMate requests an authenticated account for production use; unauthenticated access
is limited to personal/evaluation use. The free Small plan lists 100 single-hostname
queries/hour, 75/minute, 5/second and a 15-second timeout, with possible reductions
during high load. This app uses that optional account route through
`ASE_CERTIFICATE_TRANSPARENCY_KEY`, without requiring a paid plan. See the
[official pricing](https://sslmate.com/pricing/ct_search_api) and
[API authentication and pagination contract](https://sslmate.com/help/reference/ct_search_api_v1).
The app makes one request, disables wildcard/subdomain expansion and does not
paginate. Validity dates remain distinct from observation/capture timestamps.

SEC provides unauthenticated submissions data through its
[EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
The app's bounded metadata selection does not validate filing assertions. DNS uses
the [Google Public DNS JSON contract](https://developers.google.com/speed/public-dns/docs/doh/json),
and registry scope follows [Verisign's RDAP help](https://www.verisign.com/news-insights/registration-data-access-protocol/help/).
These primary contracts describe available services, not successful live probes
from this installation. Credential requests use exact HTTPS origins, no redirects
and no conditional cache, preserving the shared DNS-pinned public-address guard.
