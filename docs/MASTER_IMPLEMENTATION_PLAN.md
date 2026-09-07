# Master Implementation Plan

Maintained by the implementation-plan keeper. Phases follow `05_ROADMAP.md`; decisions of record are in `00_PROPOSAL_OVERVIEW.md` and `adr/`.

## Current status

7 September continuation: saved report-map measurements now retain original
coordinates and a versioned WGS84 method in immutable map revisions. Dashboard
and report maps share the panel and layers. Legacy revision hashes are preserved.
116 backend and 234 focused frontend tests passed, with build, type, lint and
architecture checks. The full expansion scope and remaining acceptance work are
tracked in [RESEARCH_EXPANSION_STATUS_AUDIT.md](RESEARCH_EXPANSION_STATUS_AUDIT.md).
Map-image export and current GPU acceptance remain open.

The expanded app-quality, teams, map and design milestone is completed in
[MASTER_FIX_IMPROVEMENT_PLAN.md](MASTER_FIX_IMPROVEMENT_PLAN.md), commit `cd8e498`.
Alex has since set an operator-first automated research direction with basic team
sharing, documented in [OSINT_PRODUCT_DIRECTION.md](OSINT_PRODUCT_DIRECTION.md).

Current milestone on `codex/report-evidence-scoring`:

- [x] Verify UK PHIA yardstick/confidence distinctions and the JDP 2-00 NATO grading reference.
- [x] Replace weak-padding/global-pool confidence behaviour with a per-judgement contribution matrix.
- [x] Freeze engine assessments with report versions and preserve legacy absence.
- [x] Add typed methodology/assessment responses and consistent report/export explanations.
- [x] Improve bounded selection diversity, parent caps and deterministic ordering.
- [x] Complete integrated tests, coverage, UI/document checks and final review.
- [x] Commit the verified milestone and record its actual verification below.

The matrix is application policy, not calibrated truth or full doctrinal
certification. Broader on-demand research collection remains the next product
milestone, rather than being implied by this scoring change.

Verification for this milestone: full SQLite `uv run pytest` passed 719 tests
with two PostgreSQL-only skips and 96.16 percent combined statement/branch
coverage. The focused report persistence/API/export/period/production selection
passed 53 tests on disposable PostgreSQL 17.10. Full frontend coverage passed
359 tests across 76 files using `pnpm test --maxWorkers=4`, with 98.04 percent
lines and 91.70 percent branches. The initial default-concurrency run had three
lazy-page loading timeouts during concurrent work; thresholds/defaults were not
changed. The final full frontend run includes the citation regression and aligned
fixtures; UI corrections also received real-browser checks. New core policy
modules reached 100 percent statement/branch coverage.
Ruff, mypy, import contracts, Bandit, frontend lint/types/format/build and file
limits passed. PDF pages were visually checked; DOCX content passed with office
renderer verification still outstanding. No real model or production deployment
is included in these results. All pre-commit gates, including Gitleaks, passed.
The milestone is committed on `codex/report-evidence-scoring`; no remote or push
is configured. [The review](security/REPORT_ASSESSMENT_REVIEW.md) records the scope.

Phases 0 to 4 are built. The 6 September 2026 continuation adds the remaining Phase 5 features and the Phase 6 hardening work: translation, social listening and watchlists; optional administrator TOTP, report documents and comparison, semantic search, bounded-memory performance fixes, keyboard and motion improvements, and backup/restore tooling. Live events remain in memory. The current operating instructions are in [PHASE5_PHASE6_OPERATIONS.md](PHASE5_PHASE6_OPERATIONS.md).

PIR tagging in the pipeline, plan editing in the app and baseline-relative indicators remain follow-ups. Modern opaque Google News links cannot currently be decoded without obtaining a signature from HTML, which conflicts with the no-scraping requirement. Their original Google URL is preserved. The ASVS review is a documented assessment, not certification or permission for public exposure; its remaining deployment checks are listed in [security/PHASE6_ASVS_REVIEW.md](security/PHASE6_ASVS_REVIEW.md).

Environment facts: Windows 11 host; git 2.51, Python 3.13, uv 0.11, Node 22, npm 11, Docker Desktop and the Docker CLI are installed; pnpm 11 is installed at user level through npm (corepack cannot write its shims without administrator rights); `just` and `pre-commit` are not installed (use `uvx pre-commit` and plain commands, or `uv tool install rust-just`). Backend tests run against SQLite by default and against PostgreSQL when `ASE_TEST_DATABASE_URL` points at one (CI has a PostgreSQL job). The development API runs on port 8001 with `ASE_DEV_API_TARGET` in `frontend/.env.local`, because a stale listener holds port 8000 until the host is rebooted.

Baseline before this continuation: backend 229 tests passing with 95.36 percent coverage; frontend 226 tests passing with 97.18 percent lines and 90.20 percent branches. Both coverage gates remain 90 percent.

Verification on 6 September 2026:

| Check | Result |
|---|---|
| Final SQLite backend suite | 467 passed, one PostgreSQL-only skip; 96.11 percent combined statement/branch coverage |
| PostgreSQL 17 | Full 462-test suite passed; after final report-production changes, the 36-test report/gateway selection passed with PostgreSQL configured (the writer-lock regressions deliberately use file-backed SQLite) |
| Frontend | 262 tests passed across 60 files; 97.82 percent lines, 91.34 percent branches, 97.12 percent statements, 95.49 percent functions |
| Source checks | Ruff lint/format, mypy strict, both import contracts, ESLint, TypeScript and file-length check passed; only the untouched 366-line grading module exceeds the 350-line target |
| Security tools | Python/pnpm audits found no known vulnerabilities; Bandit and Gitleaks passed; Semgrep passed with 457 applicable rules after 13 precisely documented false-positive annotations |
| Container images | Final API and web builds passed; Trivy reported no HIGH/CRITICAL findings under the recorded scan policies. Rebuilt standard Caddy retains all 132 modules; local HTTPS/static/API checks passed |
| Recovery | Real SQLite and PostgreSQL 17 CLI drills passed, including migrations 0001 to 0011, all 19 tables and decryption of recovered credentials/TOTP; original data unchanged |
| Browser | Desktop Chrome checked real globe/map tiles and markers, social, report comparison/downloads, unavailable search, admin access, keyboard focus and reduced motion using isolated synthetic data |

Container scan results and remaining deployment requirements are recorded in the
[ASVS review](security/PHASE6_ASVS_REVIEW.md). GitHub CI has not run because no
remote is configured. The PostgreSQL checks used a disposable version 17 instance,
not the operator's PostgreSQL 16/PostGIS deployment. Backup scripts separately
measured 92.89 percent branch-aware coverage.

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
- [x] Products: Disaster SITREP (hazard scope, optional country) and Conflict Assessment (conflict scope: bounding box, countries and keywords steer selection, the curated summary goes to the model as background that must not be cited; most likely and most dangerous courses of action with yardstick terms); the tracker detail pages link to a prefilled generate form
- [x] Trackers in the app: the rail entry is live; boards with activity, trend, red alerts and the latest item; detail pages with a fourteen-day timeline, the event list and "show on globe" (the "generate" buttons arrive with the tracker templates)
- [x] Globe upgrades the trackers need: aircraft icons rotated to their heading, cyclone and volcano icons, grid clustering with counts below zoom 3 (a click flies in), and a time window control (1 h to 7 d or everything retained); playback over the window is still to come

### 3b. Aviation
- [x] adsb.lol LADD and PIA lists with the database flags (military, interesting, PIA, LADD) as tags; emergency squawk polling (7500, 7700, 7600) as severe events; all traffic over eight watched areas through 250-nautical-mile point queries (`ase/resources/air_watch.json`); one event id per airframe whichever query saw it
- [ ] OpenSky anonymous bounding boxes as the fallback for the watched areas
- [x] Aircraft rendering: heading icons (with the globe upgrades) and emergency colouring
- [ ] Aircraft rendering, later: altitude colouring, short trails, callsign labels at high zoom; the Mictronics aircraft database for type and operator
- [x] Baselines: an `activity_samples` table (migration 0005) of hourly maxima written every five minutes by a background sampler (military aircraft per nation, aircraft per watched area, emergency squawks); the aviation board shows each nation and area against its 30-day mean
- [x] GNSS interference map: one-degree cells over a rolling day with the GPSJam share of poor-accuracy aircraft (`nac_p` of 5 or below is the assumption), served at `/api/trackers/aviation/jamming`
- [x] Aviation Activity Report template, with the board (counts against baselines, emergencies, interference cells) handed to the model as background
- [x] Aviation in the app: a board page (counts, nations and watched areas against baseline, emergency squawks, a link to the activity report), a GNSS interference layer on the globe refreshed every five minutes while it is on, and emergency aircraft drawn in the critical colour

### 3c. Maritime, space and cyber
- [x] Connectors: NAVAREA broadcast warnings (positions parsed from the text, kind and severity from keywords), space stations propagated with SGP4 from CelesTrak elements cached for two hours, Launch Library 2 upcoming launches at their pads, the SWPC planetary K index, ransomware.live victim claims (credibility possibly true, as criminal statements) and IODA outage alerts (critical and warning only); country-level events now sit at the nation's centroid with country-level geo confidence, so outages and claims appear on the globe; the maritime retention window grew to six hours so warnings polled every two hours survive
- [x] Boards and pages: maritime (warnings by area and kind, notable and latest), space (stations now with altitude, upcoming launches, the K index and space weather alerts), cyber (outage signals and ransomware by nation and group, the week's exploited vulnerabilities); Maritime Activity Report and Cyber Summary templates with the boards as background; the trackers page lists every module
- [ ] AISStream and Global Fishing Watch connectors behind capability flags for when the keys exist; SWPC aurora oval as a globe overlay; satellites over an area and next passes
- [ ] Sanctions context for briefs from the UK Sanctions List and OFAC SDN exports (programmes touching a country)

## Phase 4: Direction and warning

Acceptance from the roadmap: an indicator fires on synthetic data within one pipeline cycle and produces an alert and a report.

- [x] Direction domain: areas of interest (a bounding box or a set of nations), collection plans with numbered PIRs and SIRs (keywords and categories, codes assigned by the domain), matching and scope rules, and the plan's direction derived from its requirements
- [x] Persistence (migration 0006: `aois`, `collection_plans`), owner-or-admin rules in the use cases, audit actions, `/api/direction/aois` and `/api/direction/plans`
- [x] Evidence on demand: `GET /api/direction/plans/{id}` gathers the last week from the live store inside the plan's area or nations and lists the matches per SIR; nothing is precomputed or stored
- [x] Plan-scoped reports: `plan` on the report request; the plan's area, nations and keywords steer selection, its description reaches the model as uncited background, its requirements replace the direction call, and the first PIR is the question unless another is asked; the scope records the plan so regeneration repeats it
- [x] Direction in the app: the rail entry replaced its placeholder; areas and plans on one page with compact forms; a plan page with the evidence per requirement and a "Generate assessment" link into the prefilled report form
- [ ] PIR tagging of live events in the pipeline and a plan filter on the globe
- [x] Indicators: standing rules (nations or a box, categories, keywords, a severity floor, a threshold over a window, a cooldown) evaluated every minute over the live store by a background loop; alerts persist (migration 0007, pruned after 30 days), travel the stream as `alert` messages, reach an optional webhook (`ASE_ALERT_WEBHOOK_URL`, public hosts only, one POST, no retry) and can open a report as the owner; `/api/warning/indicators` and `/api/warning/alerts` with acknowledgement; a Warning page and an alert count in the shell
- [ ] Baseline-relative indicators (military aircraft or area traffic against the 30-day mean) and email routing once a transport exists
- [x] Scheduled products: standing orders (`/api/schedules`, migration 0008) for a product, a nation or a plan at a UTC hour, daily, on weekdays or weekly; a runner in the app lifespan produces each due order as its owner and books the next run, keeping the last report or the last error on the schedule; managed from the Reports page
- [x] Ops-room mode: `O` on any page opens the globe without rail or top bar, turning slowly eastward (still in lite mode or on the flat map), with the ticker, the brand mark, an exit hint and the unacknowledged alerts of the last day refreshed every minute; Escape leaves
- [ ] Editing plans in the app (the API already accepts `PUT`) and more than one PIR per form

## Known follow-ups carried forward

- Replace the hand-rolled `useResource` and `useAuditLog` hooks with TanStack Query (the architecture's choice for server state); two lint suppressions mark the spots.
- Configure a GitHub remote to get a first hosted CI run. Local Semgrep, Trivy and PostgreSQL checks now have recorded results; the hosted workflow remains unverified.
- Consider a JSON depth limit for incoming API requests alongside their body size cap, and a challenge instead of a hard lockout before any public exposure. Structured model responses already reject excessive nesting.
- deck.gl and MapLibre now have separate chunks. They remain large dependencies (about 695 KB and 957 KB minified); the application globe chunk is about 30 KB. The worker/shared assets add about 19 KB/492 KB, and deck still preloads on login because of shared runtime dependencies. Removing dependency recursion caused a browser initialisation failure, so safe ordering is retained. Further reductions remain a measured follow-up; warning thresholds were not raised.
- The live globe loads up to 2,000 events on entry and mirrors at most 5,000; revisit both caps with the retention windows when more connectors land.
- Source names are not exposed to non-admin users, so the inspector shows the source id; a public sources summary endpoint would fix that.

## Phase 5: Social and languages

Acceptance from the roadmap: foreign-language items appear with translated titles and social bursts are detected.

- [x] Social feeds without keys: Mastodon hashtag timelines on operator-chosen instances (`ase/resources/social_watch.json`; posts reduced to text, reliability E, credibility 6), outlet YouTube channels (BBC, Reuters, DW, Al Jazeera, France 24, Sky; the outlet's reliability) and subreddit listings (worldnews, geopolitics, UkrainianConflict; reliability E) as Atom seeds. Bluesky re-checked and still refused; Telegram stays out
- [x] Language detection: a pipeline stage fills the language of events whose feed could not name one (social posts first), backed by py3langid restricted to 24 languages with a confidence floor; under test the stage runs with a null detector
- [x] Translation: enabled `translation` model role, encrypted credentials, strict ordered JSON output, short-lived usage sessions and lifespan wiring; batches up to 20 titles every 30 seconds within a 60-call hourly budget, counting failed attempts. Bounded retry/cache state and compare-before-update preserve revised or expired events and live-store budgets
- [x] Social board and page: rolling-day posts by platform/instance and hashtags, latest items and located posts on the globe; hourly keyword aggregates with zero samples and 30-day retention, bounded to 32 watched terms, with bursts against earlier complete hours
- [x] Watchlists: Google News RSS search from enabled collection-plan terms, bounded to 12 deduplicated literal phrases, one request per minute, 15 minutes per query and 48 requests per rolling hour; conditional response cache bounded to 256 entries
- [x] Cited-evidence URL resolution is lazy, validates public hosts and handles legacy embedded publisher URLs without fetching publisher HTML
- [ ] Modern opaque Google News publisher URL decoding: signature-free batchexecute returned no result in the live probe; original Google links remain usable. No scraping fallback has been added

## Phase 6: Hardening and polish

- [x] Optional administrator TOTP: encrypted pending/active factor, password recheck, timed enrolment, atomic step replay prevention, session revocation and local password-confirmed recovery command (migration 0009)
- [x] PDF and DOCX downloads from frozen report versions with citations, findings, annex and review banner; bounded off-event-loop rendering; text-only processing without remote asset fetches
- [x] Version comparison for report text and frozen evidence, available in the reader
- [x] Semantic search over latest saved report versions using an optional embeddings profile, explicit small indexing batches, bounded vectors, invalidation and per-user/global budgets (migration 0010; [ADR 0008](adr/0008-bounded-report-search.md))
- [x] Performance pass: linear expiry pruning, correct 5,000-event client cap, memoised globe layers, separate map vendors; repeatable store benchmark under `backend/benchmarks/`
- [x] Accessibility review and fixes: native keyboard time controls, visible nation-field focus, skip navigation, reduced-motion and hidden-page behaviour; browser/assistive-technology limits recorded with verification
- [x] Backup and restore scripts: SQLite online snapshot including WAL, integrity/manifest checks, explicit secrets opt-in, new-target-only restore, PostgreSQL dump/restore support; [procedure](BACKUP_RESTORE.md)
- [x] Documentation refreshed, including operational limits and the bounded-search decision
- [x] ASVS 5.0 level 2 review with evidence and remediation tracking; [review and remaining gates](security/PHASE6_ASVS_REVIEW.md)
- [ ] Before exposure beyond the LAN: complete the review's remaining staging, deployment, recovery and operational checks
- [ ] DOCX visual verification in Word or LibreOffice: structural/content checks passed, but no office renderer is installed on this host

## Blockers

- No git remote yet, so CI has not run.
- No LLM endpoint or `ASE_ENCRYPTION_KEY` on the development host, so every report has been generated with a scripted model only.
- Keys only Alex can obtain, in order of visible impact: a NASA FIRMS map key (active fires, the most obvious gap on the globe), an Ordnance Survey Data Hub key (`ASE_OS_MAPS_KEY`), an AISStream key and a Global Fishing Watch token (vessels), an alerts.in.ua token (air-raid alerts), a UCDP token and an ACLED account (conflict event history), a ReliefWeb application name (the API answers 410 until it is approved), and optionally OpenSky credentials (only to poll civil traffic more often) and Cloudflare Radar (IODA covers outages without it).

## 6 September 2026: research expansion implementation milestone

- [x] Regional RSS, language catalogue and explicit collection-plan/source controls.
- [x] Admin source admission, including release-time revocation checks.
- [x] Shared frozen report maps, geographic precision disclosure, private GeoJSON
  overlays and bounded Copernicus footprint queries.
- [x] Company relationships, local designation snapshots, procurement, academic,
  parliamentary and development-indicator adapters, with explicit coverage limits.
- [x] Claim inspection, bounded evidence ZIP exports, Chinese PDF fonts and personal
  report library annotations.
- [ ] Complete the wider expansion acceptance gates and deferred features listed
  in RESEARCH_EXPANSION_IMPLEMENTATION_PLAN.md. This milestone is partial against
  that plan, not completion of every E0-E13 workstream.

See RESEARCH_EXPANSION_OPERATIONS.md for behaviour, deployment requirements and
remaining limits. Migrations 0022/0023 have not been applied to operator data.
