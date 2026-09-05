# Master Implementation Plan

Maintained by the implementation-plan keeper. Phases follow `05_ROADMAP.md`; decisions of record are in `00_PROPOSAL_OVERVIEW.md` and `adr/`.

## Current status

Phases 0 to 2 are built and committed (last commit `2fd8d22`, 5 September 2026). Phase 0 gave the foundation and auth; Phase 1 the fusion core, the live globe and the first connectors; Phase 2 the grading engine, the LLM gateway, the doctrine-validated report pipeline with versions, a Markdown download, the direction call for asks, the devil's advocacy pass and Wayback archiving. End-to-end generation against a real model is still untested because no endpoint or `ASE_ENCRYPTION_KEY` is configured on the development host.

Phase 3 (trackers) started on 5 September 2026 after a product rethink (below). The tracker domain module and its port exist; the boards, API, connectors and pages follow the checklist in the Phase 3 section.

Environment facts: Windows 11 host; git 2.51, Python 3.13, uv 0.11, Node 22, npm 11, Docker Desktop and the Docker CLI are installed; pnpm 11 is installed at user level through npm (corepack cannot write its shims without administrator rights); `just` and `pre-commit` are not installed (use `uvx pre-commit` and plain commands, or `uv tool install rust-just`). Backend tests run against SQLite by default and against PostgreSQL when `ASE_TEST_DATABASE_URL` points at one (CI has a PostgreSQL job). The development API runs on port 8001 with `ASE_DEV_API_TARGET` in `frontend/.env.local`, because a stale listener holds port 8000 until the host is rebooted.

Check results at the last run (5 September 2026): backend 182 tests passing, coverage 97.3 percent, ruff, mypy strict, import-linter, bandit (11 pre-existing low findings, all asserts and enum strings) clean; frontend 170 tests passing, coverage 97.8 percent statements and 91.1 percent branches, eslint and tsc clean, production build succeeds; pre-commit and the file-length check pass.

## Product rethink, 5 September 2026

Alex asked for a hard look at what the map can actually show, what the analysis features actually are, and which free feeds really answer. Every candidate feed was fetched live from the development host and the results are recorded in `02_DATA_SOURCES.md` section O; the feature inventories are in `04_FEATURES_AND_VIEWS.md` sections 11 and 12. What changed:

- Aviation is far richer without keys than the roadmap assumed. adsb.lol answers the military, interesting, LADD, PIA, emergency-squawk and 250-nautical-mile point queries with no key, and the aircraft records carry the integrity fields the GNSS interference map needs. OpenSky answers anonymous bounding-box queries within its 400 daily credits. Civil traffic over areas of interest, emergencies and the jam map therefore move into Phase 3 with nothing to wait for; a registered OpenSky account only raises the poll rate.
- The disaster tracker has every feed it needs: NHC and JTWC cyclones with positions, Smithsonian volcano reports with coordinates (the catalogue said they had none), tsunami bulletins with coordinates, EMSC earthquakes, NWS severe weather polygons and Met Office warnings. MeteoAlarm's Europe-wide feed is gone but its per-country Atom feeds answer, so European warnings arrive one country at a time.
- Maritime without keys is limited to NAVAREA warnings (386 active, positions in free text). NGA's anti-shipping path is gone. AIS and Global Fishing Watch stay behind free keys that only Alex can obtain, so the maritime module ships as warnings first and vessels when the keys arrive.
- Space and cyber are fully keyless: CelesTrak elements with SGP4, Launch Library 2, SWPC, IODA outage alerts, ransomware.live and CISA KEV.
- Conflict context: HDX HAPI answers with only an encoded application identifier (monthly conflict aggregates by admin area), WHO Disease Outbreak News, IFRC GO and UNHCR answer, and the UK Sanctions List and OFAC SDN exports download. ISW's current control-of-terrain layer is not discoverable as a public service (only historical ones are), so it is no longer promised. UCDP and ACLED need the token and account already listed.
- Social: Mastodon, Reddit RSS and YouTube RSS answer; the Bluesky public AppView returns 403 from this host, so Phase 5 must re-check before relying on it. Telegram stays out per decision 7.
- GDELT's DOC API rate-limits on the first call, so tone and volume sparklines come from the live store rather than from GDELT.
- Two Phase 1 promises still wait on keys that only Alex can obtain, and they are the most visible gaps on the globe: NASA FIRMS active fires and OS Maps. A configured LLM endpoint is the single most valuable thing Alex can add, because the entire reporting stack has only been exercised with a scripted model.

The revised order is: Phase 3a disaster and conflict trackers with their products and the globe upgrades they need (icons, clustering, time slider); Phase 3b aviation; Phase 3c maritime warnings, space and cyber; Phase 4 direction and warning on top of the tracker signals; Phase 5 social and languages; Phase 6 hardening. The one durable addition the architecture allows for "normal levels" (tiny hourly aggregates for baselines) lands in Phase 3b.

## Phase 0: Foundation

### Backend
- [x] `backend/pyproject.toml` with uv, ruff, mypy strict, pytest, coverage gate 90 percent, import-linter contracts
- [x] Layered skeleton `ase/{domain,application,adapters,api,infrastructure}` and `ase/container.py`
- [x] Settings (`ASE_` prefix), structured logging with redaction and tracebacks, `/api/health`, `/api/ready`
- [x] SQLAlchemy 2 async models and Alembic migration 0001 (users, account_requests, refresh_tokens, password_tokens, audit_log)
- [x] Password hashing (argon2id, parameters pinned), password policy with the 10,000 most common passwords deny list (checked on the whole password and on its core without trailing digits and punctuation, because no entry in the top 1,000 reaches the 12-character minimum)
- [x] Access tokens (JWT HS256, 15 min), refresh token rotation with family reuse detection, CSRF double-submit
- [x] Rate limiting (in-memory sliding window, LRU bounded) and account lockout
- [x] Auth endpoints: login, refresh, logout, request-account, forgot-password, set-password, me
- [x] Admin endpoints: account requests (list, approve, reject), users (list, patch, reset-link), audit log
- [x] Security headers middleware, request body cap (413), the error envelope
- [x] CLI: `ase create-admin`, `ase export-openapi`, `ase migrate`
- [x] Tests covering every endpoint and every security rule, coverage at or above 90 percent

### Frontend
- [x] Vite + React 19 + TypeScript strict + Tailwind 4 + pnpm, eslint (typescript-eslint strict, jsx-a11y, react-hooks), prettier, vitest with coverage gate 90 percent
- [x] Dark theme tokens (obsidian ground, ember accent #FF6F37, cyan data, amber warnings)
- [x] Evil Eye component copied verbatim from the React Bits registry (`EvilEye-TS-TW`) with licence header and `THIRD_PARTY_NOTICES.md`; `BrandMark` wrapper (small, frame-capped, pauses when hidden, static under reduced motion)
- [x] Auth pages: login, request account, forgot password, set password (activation and reset), all with the full-bleed Evil Eye
- [x] Auth store: access token in memory, silent refresh with CSRF header, 401 retry once, logout
- [x] App shell: left rail (Globe, Map, Trackers, Direction, Reports, Admin), top bar, brand mark
- [x] Globe page as the root route: MapLibre GL JS 6, OpenFreeMap dark style with palette overrides, `globe` projection, atmosphere; Map mode toggle to Mercator; WebGL2 fallback message
- [x] Admin pages: account requests (approve with role, reject, show activation link), users (role, active, reset link), audit log
- [x] Generated API types from the exported OpenAPI schema (`pnpm gen:api`) and a typed fetch client with zod validation at the boundary
- [x] Tests with Testing Library and MSW for every page and the auth store
- [x] Static brand assets captured from the component (favicon, apple touch icon, PWA icons, web manifest) and linked from `index.html`

### Infrastructure and repo
- [x] `.gitignore`, `.env.example`, `README.md` quick start
- [x] `docker-compose.yml` (api, web via Caddy, db postgis), `infra/Caddyfile`, non-root read-only Dockerfiles
- [x] `justfile`, `.pre-commit-config.yaml` (ruff, ruff-format, gitleaks, file-length check, frontend lint and typecheck)
- [x] `scripts/check_file_length.py` (warn at 350, fail at 400)
- [x] GitHub Actions CI: backend lint, type, test with coverage (SQLite job and PostgreSQL service job); frontend lint, typecheck, test, build; security (pip-audit, bandit, pnpm audit, gitleaks); semgrep; trivy image scans; actions pinned to commit SHAs
- [x] `SECURITY.md` at the root, `docs/DEVELOPMENT_STORY.md`

### Acceptance
- [x] A visitor requests an account; an admin approves it and receives an activation link; the user sets a password, logs in and lands on the 3D globe (verified in the embedded browser and in Chrome on 4 September 2026)
- [x] Code quality review and security review completed with findings fixed (see `DEVELOPMENT_STORY.md`)
- [x] All checks green locally; coverage at or above 90 percent on both sides

## Phase 1: Fusion core and globe data

### Backend fusion core
- [x] Unified `Event` model with grade, provenance, geo confidence, severity and frozen attributes; `SourceSpec` and the source registry
- [x] Ports for connectors, the event store and the event bus; in-memory store with per-category retention windows, caps and a memory budget; in-memory bus
- [x] Normaliser pipeline, health registry with circuit breakers, feed scheduler (timeouts, jitter, backoff, resume), hardened feed HTTP client (SSRF guard, size caps, conditional requests)
- [x] Starter connectors without keys: USGS earthquakes, GDACS, NASA EONET, NOAA SWPC alerts and scales, CISA KEV
- [x] `/api/events`, `/api/events/stats`, `/api/stream` (server-sent events with a token-lifetime deadline), `/api/admin/sources` with reset
- [x] Feeds start and stop with the application lifespan; `ASE_FEEDS_*` settings; tests with fixtures only (no live network)
- [x] Generic RSS 2.0, RDF and Atom connector with 21 seeded sources verified live on 5 September 2026: GOV.UK FCDO news and travel advice, US State travel advisories (country codes from the feed), UN News, UN press, ReliefWeb updates RSS, Crisis Group, and outlets (BBC, DW, France 24, Al Jazeera, Guardian, Le Monde, SCMP, Nikkei Asia, Times of Israel, Anadolu, Dawn, Meduza, Ukrainska Pravda, TASS flagged state controlled)
- [x] GDELT 2.0 events connector: follows `lastupdate.txt` to the newest export zip (size-checked), keeps protest and conflict CAMEO root codes, grades C with credibility from the source count; the GEO API answers 404 and the DOC API is limited to one call per five seconds, so neither is used
- [x] Military aircraft from adsb.lol's v2 `mil` endpoint (no key; airplanes.live answered 403 from this host): one event per ICAO hex that moves on every 60-second poll and expires with the ten-minute aviation window
- [ ] More connectors: OpenSky (OAuth2), ADS-B area-of-interest queries, Google News RSS editions, more outlets in more languages (Kyiv Independent, Focus Taiwan, NHK World, ISW and Kyodo answered 404 or 403 and need confirmed URLs), NASA FIRMS (key), EMSC
- [x] Country resolution: Natural Earth 1:110m admin-0 polygons packaged as a 175 KB resource (built by `scripts/build_countries.py`, public domain), a pure point-in-polygon in the domain, a bounding-box index in an adapter, a pipeline stage that fills `country_iso` on located events, and `/api/countries` for the frontend
- [ ] Admin source overrides persisted (enable, disable, interval)

### Frontend live globe
- [x] zod schemas for events, stats, sources and stream payloads; typed events API module
- [x] Fetch-based server-sent events client with bearer auth, reconnect with backoff, and a fresh token on `bye` or 401
- [x] Events store: bounded client mirror (5,000), upsert and expiry from the stream, category visibility, selection
- [x] deck.gl `MapboxOverlay` on the MapLibre engine; one scatterplot layer per category from the layer registry (shared colours)
- [x] Layer panel with per-category switches, counts, store budget and connection status; ticker of the latest events; event inspector (grade with rationale, provenance, summary, attributes, tags, http(s) links only)
- [x] Tests for the parser, client, store, registry, panels and the page with the overlay and stream client mocked; live globe confirmed in the browser against the dev API
- [x] Nation filter (name or code, Enter completes a prefix) that scopes the layers, counts and ticker to one nation and flies the camera to it; country panel v1 with per-category counts and the latest events for that nation
- [x] Day and night terminator (solar position from the clock, the night hemisphere as one deck.gl polygon refreshed every half minute), lite mode (no atmosphere, no camera animation, no terminator, brand mark held still) and a WGS84 coordinate readout that copies on click; base layer, terminator and lite mode persist in the browser, the view mode never does
- [ ] MGRS and OS grid reference in the coordinate readout
- [x] Base-layer switcher: EOX Sentinel-2 cloudless satellite, hybrid (imagery under the vector boundaries and labels), and OS Maps Road, Outdoor and Light raster tiles proxied through `/api/tiles/os` with the key server-side, a byte-bounded cache and validated addresses (`/api/capabilities` tells the browser whether a key exists; the session token is attached to tile requests to our own origin only)
- [ ] NASA GIBS daily imagery with a date picker; the mandatory OS logo alongside the OS attribution line
- [x] Admin source page: every feed with its organisation, category, grade, poll interval, health status, last poll, last error and a reset button that clears the circuit breaker
- [ ] Replace `useResource` and `useAuditLog` with TanStack Query

## Phase 2: Grading and reporting

### Grading engine
- [x] Story clustering: stemmed title tokens with Jaccard similarity inside a 48-hour window (any category), plus same-subtype events within 150 km and 12 hours for disasters; deterministic story ids
- [x] Credibility per doctrine section 4.3: confirmed with two or more independent corroborations, probably true with one, instruments and authoritative registries probably true, state-controlled or interested-party single sources possibly true, other single sources possibly true when consistent with the picture (same country or within 150 km, same category, same window) and otherwise cannot be judged; independence by parent organisation with near-identical text across organisations folded as syndication; a rationale string on every item
- [x] Regrading runs after every poll for the categories the batch touched and republishes neighbours whose grade moved; grades are recomputed as items arrive
- [ ] Contradiction rules (doubtful, improbable) and instrument anomaly flags; corroboration and contradiction identifiers on the event

### Reports
- [x] LLM gateway: profiles for any OpenAI-compatible endpoint (name, base URL, model, roles, token and temperature limits), keys encrypted with Fernet under `ASE_ENCRYPTION_KEY` and shown only as a four-character hint, migration 0002, a connection test that must answer `{"ok": true}` through JSON-schema output, a usage log, audit entries, and the admin Models page (create, edit without resending the key, test, two-step delete)
- [x] Doctrine vocabulary as matchers (yardstick bands with ranges, forbidden ICD 203 phrases, hedges, confidence phrases), the report body schema (JSON schema for the model plus a lenient parser), the linter (one term per judgement matching its probability, no hedges, confidence separate and never in the same sentence, reporting cites and contains no terms, unknown citations stripped, no foreign URLs, assumptions and alternatives required, confidence capped by the information base, change_from_previous when a previous version exists, length budgets)
- [x] Templates as typed rows (INTSUM, INTREP, Country Brief, Ask the Eye) with evidence strategy and token budget; evidence selection by grade, recency, severity and per-source diversity with instruction-like text screened out; frozen evidence items; quality-of-information statistics with a confidence ceiling; prompt composition with the doctrine preamble; generation with one retry carrying the validator's findings, then needs_review or failed
- [x] Persistence in migration 0003 (reports, report_versions with body, findings, evidence and quality as JSON plus the rendered Markdown), the reports API (templates, generate, list, read, Markdown export, delete by owner or admin, ten generations per user per hour), usage and audit entries
- [x] Reports in the app: a generate form (product, nation, window, question), the list with status badges, and a reader with judgements (yardstick term and confidence chips, evidence labels), reporting, assessment, assumptions, alternatives, indicators, gaps, sourcing, validator findings and the evidence annex with http(s) links only; Markdown copied to the clipboard; owner or admin delete
- [x] Version history on regeneration (a further version keeps the scope, sees the previous key judgements and must state what changed) and a Markdown download in the reader
- [x] Wayback archiving (background task after generation: availability check, then Save Page Now; `ASE_ARCHIVE_ENABLED`), devil's advocacy pass (opt-in per report; can lower KJ1 confidence, never raise it), direction call for free-form asks (PIR, SIRs, EEIs and search terms that steer selection)
- [ ] Evidence preview before generation for asks (show the direction call's selection to the user first)

## Phase 3: Trackers

Acceptance from the roadmap: each tracker has a board, a detail view, a globe layer and a report template. Feeds are the ones verified in `02_DATA_SOURCES.md` section O.

### 3a. Framework, disasters and conflicts
- [x] Tracker domain: hazards folded from connector subtypes, curated `Conflict` definitions, activity (24 h, 7 d, previous 7 d, trend), day buckets, hazard and conflict cards computed from the live store, never stored
- [x] Curated conflicts and tension areas as a packaged resource (Ukraine, Gaza and the West Bank, Israel and Hezbollah, Sudan, Yemen and the Red Sea, the central Sahel, eastern DR Congo, Myanmar, Somalia, Syria, Haiti, Ethiopia, north-east Nigeria, Cabo Delgado, Libya, Taiwan Strait, the Korean peninsula, the South China Sea, India and Pakistan, Armenia and Azerbaijan, Colombia, the Pakistan and Afghanistan border, Iran and Israel), each with countries, a bounding box, belligerents, keywords and a summary; admin editing is a later follow-up
- [x] Tracker service and API: `/api/trackers/disasters`, `/api/trackers/disasters/{hazard}`, `/api/trackers/conflicts`, `/api/trackers/conflicts/{id}` with cards, timelines and the events behind them
- [x] Connectors: NHC and JTWC cyclones (positions, intensity, movement), Smithsonian weekly volcano reports, NTWC and PTWC tsunami bulletins, EMSC earthquakes, NWS severe weather, WHO Disease Outbreak News, IFRC GO events (ten sources, each tested against a captured sample)
- [ ] Met Office UK warnings and MeteoAlarm per-country feeds (both answer but were empty or unseen at capture time, so no parser is written yet); HDX HAPI monthly conflict aggregates for the conflict detail view
- [ ] Products: Disaster SITREP (hazard scope, optional country) and Conflict Assessment (conflict scope: bounding box, countries and keywords steer selection; most likely and most dangerous courses of action with yardstick terms)
- [x] Trackers in the app: the rail entry is live; boards with activity, trend, red alerts and the latest item; detail pages with a fourteen-day timeline, the event list and "show on globe" (the "generate" buttons arrive with the tracker templates)
- [ ] Globe upgrades the trackers need: cyclone and volcano icons, clustering or hex density at low zoom, a time slider over the retained window

### 3b. Aviation
- [ ] adsb.lol interesting, LADD and PIA lists; emergency squawk polling (7700, 7600, 7500) as alerts; area-of-interest civil traffic through 250-nautical-mile point queries around seeded areas, with OpenSky anonymous bounding boxes as the fallback
- [ ] Aircraft rendering: heading icons, altitude colouring, short trails, callsign labels at high zoom; the Mictronics aircraft database for type and operator
- [ ] Baselines: tiny hourly aggregates of military flights per country and emergencies per region (the one durable "normal levels" table); per-country activity against a 30-day baseline on the aviation board
- [ ] GNSS interference hex map from `nac_p` and `nic`, updated hourly
- [ ] Aviation Activity Report template

### 3c. Maritime, space and cyber
- [ ] NAVAREA warnings with positions parsed from text as points and areas; Maritime Activity Report template; AISStream and Global Fishing Watch connectors behind capability flags for when the keys exist
- [ ] Space: CelesTrak groups propagated with SGP4 (satellites over an area now and next passes, ISS and chosen groups' ground tracks), Launch Library 2 launch sites with countdowns, SWPC aurora oval and K index; space summary in the country and area panels
- [ ] Cyber: IODA outage alerts by country and region on the globe, ransomware victims by country and group, CISA KEV summary; Cyber Summary template
- [ ] Sanctions context for briefs from the UK Sanctions List and OFAC SDN exports (programmes touching a country)

## Known follow-ups carried forward

- Replace the hand-rolled `useResource` and `useAuditLog` hooks with TanStack Query (the architecture's choice for server state); two lint suppressions mark the spots.
- Push to GitHub to get a first CI run; several workflow steps (semgrep, trivy, the PostgreSQL job) have never executed.
- Consider a JSON depth limit alongside the body size cap, and a challenge instead of a hard lockout before any public exposure.
- Split deck.gl and MapLibre into their own chunks (the globe chunk is 1.6 MB minified) once the layer set settles.
- The live globe loads up to 2,000 events on entry and mirrors at most 5,000; revisit both caps with the retention windows when more connectors land.
- Source names are not exposed to non-admin users, so the inspector shows the source id; a public sources summary endpoint would fix that.

## Later phases

See `05_ROADMAP.md` and the revision note at its end: Phase 3 trackers in three slices (3a disasters and conflicts, 3b aviation, 3c maritime warnings, space and cyber), Phase 4 direction and warning on top of the tracker signals, Phase 5 social and languages, Phase 6 hardening.

## Blockers

- No git remote yet, so CI has not run.
- No LLM endpoint or `ASE_ENCRYPTION_KEY` on the development host, so every report has been generated with a scripted model only.
- Keys only Alex can obtain, in order of visible impact: a NASA FIRMS map key (active fires, the most obvious gap on the globe), an Ordnance Survey Data Hub key (`ASE_OS_MAPS_KEY`), an AISStream key and a Global Fishing Watch token (vessels), an alerts.in.ua token (air-raid alerts), a UCDP token and an ACLED account (conflict event history), a ReliefWeb application name (the API answers 410 until it is approved), and optionally OpenSky credentials (only to poll civil traffic more often) and Cloudflare Radar (IODA covers outages without it).
