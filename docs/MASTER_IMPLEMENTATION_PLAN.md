# Master Implementation Plan

Maintained by the implementation-plan keeper. Phases follow `05_ROADMAP.md`; decisions of record are in `00_PROPOSAL_OVERVIEW.md` and `adr/`.

## Current status

Phase 0 (Foundation) was built on 3 and 4 September 2026 after Alex approved the plan with two amendments: the 3D globe is the default view, and the logo is specifically the React Bits Evil Eye component. The acceptance flow has been exercised end to end in a browser: a visitor requested an account, the administrator approved it and received the activation link, the new user set a password, signed in and landed on the 3D globe. Both reviews (code quality and security) ran and their findings are fixed and committed.

Phase 1 (fusion core and globe data) started on 4 September 2026 and its first two milestones are in place: the backend fusion core (unified event model, bounded in-memory store, scheduler with circuit breakers, five keyless connectors, the events API and the server-sent event stream) and the live globe (deck.gl markers over MapLibre, layer panel, ticker, inspector and a streaming client with token refresh). The compose stack has now been verified with Docker Desktop running: migrations ran on PostgreSQL, the API container reports healthy, and Caddy serves the SPA and passes the API through with the right headers on each.

Environment facts: Windows 11 host; git 2.51, Python 3.13, uv 0.11, Node 22, npm 11, Docker Desktop and the Docker CLI are installed; pnpm 11 is installed at user level through npm (corepack cannot write its shims without administrator rights); `just` and `pre-commit` are not installed (use `uvx pre-commit` and plain commands, or `uv tool install rust-just`). Backend tests run against SQLite by default and against PostgreSQL when `ASE_TEST_DATABASE_URL` points at one (CI has a PostgreSQL job).

Check results at the last run (5 September 2026): backend 123 tests passing on SQLite and on PostgreSQL, coverage 96.7 percent, ruff, mypy strict, import-linter, bandit and pip-audit clean; frontend 113 tests passing, coverage 97.4 percent statements and 93.9 percent branches, eslint and tsc clean, production build succeeds (the lazy globe chunk is 1.6 MB minified because it carries MapLibre and deck.gl); pre-commit and the file-length check pass.

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
- [ ] More connectors: OpenSky (OAuth2), ADS-B (adsb.lol, airplanes.live), Google News RSS editions, more outlets in more languages (Kyiv Independent, Focus Taiwan, NHK World, ISW and Kyodo answered 404 or 403 and need confirmed URLs), NASA FIRMS (key), EMSC
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
- [ ] Day and night terminator; lite mode; coordinate readout
- [ ] Base-layer switcher: OS Maps proxy, EOX satellite, GIBS, hybrid
- [ ] Admin source page in the UI
- [ ] Replace `useResource` and `useAuditLog` with TanStack Query

## Known follow-ups carried forward

- Replace the hand-rolled `useResource` and `useAuditLog` hooks with TanStack Query (the architecture's choice for server state); two lint suppressions mark the spots.
- The bootstrap session refresh fires even when no CSRF cookie exists, producing a harmless 403 in the console on first visit; skip the call when the cookie is absent.
- Push to GitHub to get a first CI run; several workflow steps (semgrep, trivy, the PostgreSQL job) have never executed.
- Consider a JSON depth limit alongside the body size cap, and a challenge instead of a hard lockout before any public exposure.
- Split deck.gl and MapLibre into their own chunks (the globe chunk is 1.6 MB minified) once the layer set settles.
- The live globe loads up to 2,000 events on entry and mirrors at most 5,000; revisit both caps with the retention windows when more connectors land.
- Source names are not exposed to non-admin users, so the inspector shows the source id; a public sources summary endpoint would fix that.

## Later phases

See `05_ROADMAP.md`: Phase 1 fusion core and globe data, Phase 2 grading and reports, Phase 3 trackers, Phase 4 direction and warning, Phase 5 social and languages, Phase 6 hardening.

## Blockers

- No git remote yet, so CI has not run.
