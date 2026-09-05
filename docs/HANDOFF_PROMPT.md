# Handoff prompt: continue building The All Seeing Eye

Historical snapshot from 5 September 2026. The continuation through Phase 6 is now
implemented. Read [the live plan](MASTER_IMPLEMENTATION_PLAN.md),
[operations guide](PHASE5_PHASE6_OPERATIONS.md) and
[security review](security/PHASE6_ASVS_REVIEW.md) for the current state and remaining
verification gates before using the older brief below.

Paste everything below the line into GPT-6 Astra, Codex or any other agent that will
carry on the work. It is written to be self-contained: the repository, the conventions,
what exists, what is half done, what is next, and the traps that cost time.

---

You are continuing an existing, working codebase. Read this whole brief before touching
anything, then read the repository documents it points at. Do not restart, redesign or
rewrite what already works. Do not add cloud services or paid APIs.

## 1. The product

**The All Seeing Eye** (code name `ase`) is a self-hosted OSINT fusion web app built for
one person, Alex Orr, on a Windows 11 machine at `C:\AlexDev\OSINT`. Free feeds from
around the world land on a 3D globe, are graded with NATO doctrine, and an LLM writes
doctrine-compliant assessments from frozen evidence.

Hard constraints Alex set, which must not be relitigated:

- Hobby scale, one person, self-hosted. It must not build a huge database on his machine.
- Only AI reports and configuration are persisted. Live events live in a bounded
  in-memory store and are never written to the database.
- Free data sources only, feeds and APIs only, no scraping.
- SOLID applied pragmatically, secure by design, readable and maintainable code.
- The 3D globe is the default view and the root route.
- The brand mark is the React Bits Evil Eye component, never a redrawn imitation.

The approved design lives in `docs/`. Read in this order before your first change:
`docs/00_PROPOSAL_OVERVIEW.md`, `docs/MASTER_IMPLEMENTATION_PLAN.md` (the live
checklist), `docs/01_ARCHITECTURE.md`, `docs/07_SECURITY_BY_DESIGN.md`,
`docs/DEVELOPMENT_STORY.md` (a chronological record you must keep adding to),
`docs/02_DATA_SOURCES.md` (section O is a live probe of every candidate feed),
`docs/04_FEATURES_AND_VIEWS.md` (sections 11 and 12 are the honest feature inventory).
`CLAUDE.md` at the repository root holds the same conventions in short form.

## 2. Stack and layout

```
backend/    Python 3.12+, FastAPI, SQLAlchemy 2 async, Alembic, uv, pytest, mypy strict,
            ruff, import-linter, bandit.  src/ase/{domain,application,adapters,api,
            infrastructure,container,resources}
frontend/   React 19, TypeScript strict, Vite, Tailwind 4, MapLibre GL 6 + deck.gl 9,
            zustand, zod, vitest, MSW, pnpm.  src/{app,features,components,lib,stores}
infra/      Caddyfile, Dockerfiles.  docker-compose.yml at the root (PostgreSQL + Caddy).
docs/       Design, ADRs, the plan, the development story, API contracts.
scripts/    check_file_length.py and OpenAPI helpers.
```

Development runs on SQLite (`data/ase.db`); Compose runs PostgreSQL. Tests use SQLite in
memory.

## 3. Conventions that are not negotiable

- **Layering, enforced by import-linter**: `domain` imports nothing from other layers;
  `application` imports `domain` only; `adapters`, `api` and `infrastructure` may import
  `application` and `domain`. Frontend features never import each other; they share
  through `components`, `lib` and `stores`.
- **Ports and adapters**: ports are `typing.Protocol` classes in
  `backend/src/ase/application/ports/`; adapters implement them; the `ase.container`
  package is the only place that wires concrete classes. It is a package, not a module:
  `container/__init__.py` holds the core (settings, engine, session factory, repositories,
  auth and admin factories) and `container/features.py` holds a `FeatureWiring` mixin with
  the report, tracker, direction, warning and schedule factories. The mixin declares the
  core attributes it borrows inside `if TYPE_CHECKING:` so it type-checks alone without a
  circular import. Keep that shape.
- **File length**: 350 lines target, 400 hard maximum. `python scripts/check_file_length.py`
  fails CI above 400. Split by responsibility, never by line count.
- **Thin routers and components.** Business rules live in use cases (backend) and hooks or
  stores (frontend).
- **Security**: never log or echo secrets; never render HTML from data (the only HTML path
  is report Markdown through DOMPurify); validate at boundaries; check authorisation at
  object level in the application layer, not only at the route; every outbound fetch goes
  through the SSRF guard in `adapters/feeds/http.py` (`assert_public_host` then `pin_url`).
- **Tests**: pytest and vitest, no live network (fixtures and MSW). Coverage gates are 90
  percent on both sides and must not be lowered. Backend coverage sits near 96 percent,
  frontend branches near 90, so new pages need state tests or the gate fails.
- **Types**: mypy strict, TypeScript strict. Frontend API types are generated from the
  backend OpenAPI schema (`pnpm gen:api`); never hand-write DTOs.
- **Environment variables** use the `ASE_` prefix and are documented in `.env.example`.
  No secrets in the repository.
- **UK English everywhere**, including UI copy, comments and commit messages. No em
  dashes. Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). No
  attribution or co-author lines in commit messages.
- Never claim something was tested, built or committed unless it actually happened.

## 4. Commands

```
Backend:   cd backend && uv sync
           uv run pytest                       (coverage gate 90, SQLite in memory)
           uv run ruff check . && uv run ruff format --check . && uv run mypy src
           uv run lint-imports
           uv run ase create-admin --email you@example.com --display-name "You"
           uv run ase export-openapi ../frontend/src/lib/api/openapi.json
           uv run uvicorn ase.main:app --reload --port 8001
Frontend:  cd frontend && pnpm install
           pnpm dev | pnpm test | pnpm lint | pnpm typecheck | pnpm build | pnpm gen:api
Stack:     docker compose up --build
Repo:      python scripts/check_file_length.py ; uvx pre-commit run --all-files
```

## 5. What is built (Phases 0 to 4 complete, all committed on `main`)

Recent commits, newest first: `79e532a` social listening feeds and language detection,
`564dbac` ops-room mode, `52fd3a4` scheduled products, `d63aad6` indicators and alerts,
`74e76ce` areas of interest and collection plans, `4b7ff0e` Phase 3 complete.

**Phase 0, foundation.** Layered FastAPI service, argon2id passwords, 15-minute access
tokens, rotating refresh tokens with family revocation, CSRF, rate limits, lockout,
admin-approved account requests, an audit log, and the React shell with the Evil Eye
login, the globe and the left rail. Docker Compose verified.

**Phase 1, fusion core.** A unified `Event` model, a bounded in-memory store with
per-category retention budgets and a prune loop, a scheduler with circuit breakers, an
in-process bus, server-sent events at `/api/stream`, Natural Earth country resolution, an
OS Maps tile proxy, and the live globe (deck.gl markers, layer panel, ticker, inspector,
nation filter, country panel, base layers, day-night terminator, lite mode).

**Phase 2, grading and reports.** Story clustering and doctrine credibility grading;
LLM profiles with Fernet-encrypted keys and an admin Models page; the PHIA yardstick and
confidence vocabulary as code; a validator that refuses bad judgements; templates INTSUM,
INTREP, Country Brief and Ask the Eye; evidence selection and freezing; generation with
retry; version history with regeneration and Markdown download; a direction call for asks
(PIR, SIRs, EEIs, search terms; profile role `direction`); an opt-in devil's advocacy pass
(role `devil`, may only lower the first key judgement's confidence); Wayback archiving as
a background task (`ASE_ARCHIVE_ENABLED`).

**Phase 3, trackers.** Boards computed from the live store on request, never stored, for
nine hazards and 23 curated conflicts (`ase/resources/conflicts.json`), each with a detail
page, a fourteen-day timeline and a globe scope. Twenty-nine connectors in
`adapters/feeds/registry.py` including NHC and JTWC cyclones, Smithsonian volcanoes, the
two tsunami centres, EMSC, NWS, WHO Disease Outbreak News, IFRC GO, NAVAREA warnings
(positions parsed from free text), CelesTrak satellites propagated with SGP4, Launch
Library 2, the planetary K index, ransomware.live and IODA outages, plus the adsb.lol
family (military, LADD, PIA, emergency squawks, and 250-nautical-mile area queries over
eight watched areas in `ase/resources/air_watch.json`). Hourly baselines in the one
durable aggregate table (`activity_samples`, migration 0005) written by a five-minute
sampler; a GPSJam-style GNSS interference map; aviation, maritime, space and cyber boards
and pages; templates Disaster SITREP, Conflict Assessment, Aviation Activity, Maritime
Activity and Cyber Summary. Globe upgrades: icons rotated to track, low-zoom grid
clustering with counts, a time window control, country-level events placed at centroids.

**Phase 4, direction and warning.** All of it is live:

- `domain/collection.py`: areas of interest (a bounding box or a set of nations) and
  collection plans with numbered PIRs and SIRs (codes assigned by the domain, never typed).
  Migration 0006. Owner-or-admin rules. `/api/direction/aois` and `/api/direction/plans`.
- Evidence on demand: `GET /api/direction/plans/{id}` queries the last week from the live
  store inside the plan's area or nations and lists matches per SIR. Nothing precomputed.
- Plan-scoped reports: `plan` on the report request. The plan's area and nations select
  evidence, its keywords rank it, its description reaches the model as uncited background,
  its requirements replace the direction call, and the first PIR becomes the question.
- `domain/warning.py`: indicators (nations or a box, categories, keywords, a severity
  floor, a threshold over a window, a cooldown) and alerts. Migration 0007. An evaluator
  loop started in the app lifespan runs every minute over the live store. An alert takes
  four routes: stored (pruned after 30 days), published on the bus so the stream carries
  it as an `alert` message, sent to a webhook when `ASE_ALERT_WEBHOOK_URL` is set (public
  hosts only, one POST, no retry), and turned into a report as the indicator's owner when
  the indicator names a template. `/api/warning/indicators` and `/api/warning/alerts`
  with acknowledgement. A `/warning` page and an alert count in the top bar.
- `domain/schedules.py`: standing orders for a product at a UTC hour, daily, weekdays or
  weekly. Migration 0008. A runner in the lifespan produces due orders as their owner and
  books the next run, keeping the last report id or the last error. `/api/schedules` and a
  Schedules section on the Reports page.
- Ops-room mode: `O` on any page opens the globe with no rail and no top bar, turning
  slowly eastward (the engine gained `spin`, which eases fifteen degrees every thirty
  seconds and chains on `moveend`), with the ticker, the brand mark, an exit hint and the
  unacknowledged alerts of the last day. Escape leaves. The flag is never persisted.

**Phase 5, started.** Committed in `79e532a`: Mastodon hashtag timelines from
`ase/resources/social_watch.json` (posts reduced to text, reliability E, credibility 6),
outlet YouTube channels (BBC, Reuters, DW, Al Jazeera, France 24, Sky) and subreddit
listings (worldnews, geopolitics, UkrainianConflict) as Atom seeds in
`adapters/feeds/rss_seeds_social.py`, and a pipeline `LanguageStage` that fills the
language of events whose feed could not name one, backed by py3langid restricted to 24
languages with a confidence floor (lingua was tried first and dropped because its wheel
installs 291 MB of models). Under test the container uses a null detector.

Migrations 0001 to 0008. Routers: auth, me, events, countries, capabilities, tiles,
reports, stream, trackers, direction, warning, schedules, health and five admin routers.

## 6. Uncommitted work in progress, finish this first

`git status` will show these. They are written, typed, linted and unit-tested, but not
wired into the container or the app, so the feature does not exist end to end yet.

- `backend/src/ase/application/ports/translate.py`: a `Translator` protocol
  (`translate(items: Sequence[tuple[str, str]]) -> list[str | None]`) and
  `TranslatorUnavailable`.
- `backend/src/ase/application/translate/queue.py`: `TranslationQueue`, a background loop
  that every 30 seconds takes up to 20 events from the last 24 hours whose language is
  known, not English, and which have no `title_en`, translates them in one call,
  deduplicates repeated titles inside a batch, caches by (language, title), keeps an
  hourly call budget of 60, writes results back with `store.put` (not `upsert`, because
  the content hash is unchanged) and publishes an `event.upsert` bus message so open pages
  update. `backend/tests/test_translation.py` covers it and passes.
- `backend/src/ase/domain/llm.py`: a new `LlmRole.TRANSLATION`.
- Frontend: the ticker, tracker rows and country panel now prefer `title_en ?? title`.

To finish the translation slice:

1. Write `backend/src/ase/adapters/llm/translator.py` (or similar) implementing
   `Translator` against the existing `LlmGateway`: pick an enabled profile with the
   `translation` role, decrypt its key with the cipher, send one JSON-schema request that
   returns an array of English strings in order, and record a usage row with purpose
   `translation` exactly as `application/reports/production.py` does. Raise
   `TranslatorUnavailable` when no profile plays the role or no encryption key is set.
   Model the prompt on `application/reports/direction.py`, which shows the request shape,
   the schema and the error handling.
2. Wire it in `container/features.py` (a `build_translation_queue` factory beside
   `build_evaluator` and `build_schedule_runner`) and start and stop it in the lifespan in
   `src/ase/main.py`, next to the evaluator and the schedule runner.
3. Add an API or admin surface only if the plan asks for one; the translation is invisible
   apart from `title_en`.
4. Export the OpenAPI schema, run `pnpm gen:api`, and run both suites.

## 7. What is left, in order

The live checklist is `docs/MASTER_IMPLEMENTATION_PLAN.md`. Keep it ticked and add a dated
entry to `docs/DEVELOPMENT_STORY.md` for every slice you finish.

**Phase 5, remaining.**

- The translator adapter and wiring described above.
- A social board and page: posts by platform and instance, the day's top hashtags, and
  burst detection (keyword counts against the hourly baselines in `activity_samples`,
  which already has the sampler pattern in `application/trackers/aviation.py`). A globe
  layer for posts that carry a location.
- Watchlists: keyword collection through Google News RSS search feeds built from the
  enabled collection plans' search terms. Google News article links are encoded and need
  decoding through Google's `batchexecute` endpoint, so decode lazily and only for cited
  evidence.

**Phase 6, hardening.** Optional TOTP for admins, PDF and DOCX export, report diffing,
semantic search over reports, a performance pass, an accessibility audit, backup and
restore scripts, a documentation pass, and a review against OWASP ASVS level 2 before any
exposure beyond the LAN.

**Carried forward, small and worth doing.**

- PIR tagging of live events in the pipeline and a plan filter on the globe.
- Editing collection plans in the app (the API already accepts `PUT`) and more than one
  PIR per form.
- Baseline-relative indicators (military aircraft or area traffic against the 30-day mean)
  and email alert routing once a mail transport exists.
- Met Office UK and MeteoAlarm per-country parsers (both answer but were empty at capture
  time), HDX HAPI monthly conflict aggregates, OpenSky anonymous bounding boxes as the
  aviation fallback, the SWPC aurora oval as a globe overlay, sanctions context for briefs
  from the UK Sanctions List and OFAC SDN exports.
- Replace the hand-rolled `useResource` and `useAuditLog` hooks with TanStack Query (two
  lint suppressions mark the spots).
- Split deck.gl and MapLibre into their own chunks; the globe chunk is about 1.6 MB.
- A public sources summary endpoint so non-admin users see source names, not ids.

**Blockers only Alex can clear.** No git remote yet, so the CI workflows (tests on SQLite
and PostgreSQL, lint, type checks, semgrep, trivy, dependency audits) have never run. No
LLM endpoint is configured, so end-to-end generation with a real model is still untested;
everything is proven with a scripted gateway in tests. Free keys still to obtain, in order
of visible impact: NASA FIRMS (active fires, the most obvious gap on the globe), Ordnance
Survey Data Hub, AISStream and Global Fishing Watch, alerts.in.ua, UCDP and ACLED, and a
ReliefWeb application name.

## 8. Feed reality, verified by live probes

Working without a key: adsb.lol (military, LADD, PIA, squawks, point queries), OpenSky
anonymous bounding boxes, NGA broadcast warnings, CelesTrak GP JSON (refuses repeats
inside two hours, so cache), Launch Library 2, EMSC, NHC and JTWC, Smithsonian volcanoes,
the two tsunami centres, NWS alerts (no `limit` parameter), GIBS tiles, RainViewer,
ransomware.live, IODA, NVD, Polymarket, WHO Disease Outbreak News (needs
`$orderby=PublicationDate desc`), HDX HAPI, IFRC GO, UNHCR, UK Sanctions List, OFAC SDN,
Google News RSS, Mastodon, Reddit RSS, YouTube RSS, Overpass, geoBoundaries, Wikimedia
pageviews.

Not answering from this host: the Bluesky public AppView (403 with and without a
User-Agent, re-checked at the start of Phase 5, so Bluesky stays out until a later probe
answers), the ISW current control layer, Kyiv Independent feeds, Focus Taiwan, GDELT DOC
(429 on the first call; the raw 2.0 export zips work), ReliefWeb without an approved
appname, Copernicus EMS, FEWS NET, airplanes.live (403). Telegram stays out by decision.

Reddit rate-limits (429) when several subreddit feeds are polled within seconds, which is
why each polls on its own quarter-hour.

## 9. Environment traps that cost real time

- The Bash tool's working directory persists between calls and a backgrounded command
  inherits the previous call's directory. Always `cd` to an absolute path inside the
  command itself.
- Heredocs over roughly 8 KB get truncated. Split the file or use a write tool.
- A double backslash inside a Bash heredoc collapses to one. Use `chr(92)` in embedded
  Python when you need a literal backslash.
- Python's `write_text` on Windows writes CRLF. Write bytes instead.
- Vitest with one worker per core makes the shell-heavy page tests time out on this
  machine. `vitest.config.ts` sets `maxWorkers: '50%'`; leave it.
- Coverage needs `concurrency = ["greenlet", "thread"]` for SQLAlchemy async.
- MapLibre 6 needs `optimizeDeps.exclude: ['maplibre-gl']` under Vite dev or its worker
  never loads.
- Several uvicorn processes can bind 127.0.0.1:8000 at once on this host and a stale one
  keeps answering with old code. Run the dev API on 8001 and set
  `ASE_DEV_API_TARGET=http://127.0.0.1:8001` in `frontend/.env.local`. Uvicorn `--reload`
  also stops noticing edits after a while and needs a restart.
- Test helpers shared between test modules belong in `backend/tests/*_helpers.py`.
  `make_event(key, ...)` takes a key, not an id; the id is a hash, so look events up by
  `event.id`. `good_body()` copies shallowly, so build variants with
  `good_body(key_judgements=[...])` rather than mutating it.
- Docker Hub pulls through Docker Desktop's proxy time out and need retries.

## 10. How to know you have not broken anything

Before every commit, from a clean working tree:

```
cd backend && uv run ruff format . && uv run ruff check . && uv run mypy src && uv run lint-imports && uv run pytest
cd ../frontend && pnpm lint && pnpm typecheck && pnpm test
cd .. && python scripts/check_file_length.py
```

At the last full run: backend 229 tests passing, coverage 95.4 percent; frontend 226 tests
passing, coverage 96.5 percent lines and 90.2 percent branches. Both gates are 90 percent and
must not be lowered. If a new page drops frontend branch coverage, add state tests (error,
empty and edge branches) rather than touching the threshold.

Then commit in conventional style with a short body saying what changed and why, update
`docs/MASTER_IMPLEMENTATION_PLAN.md` and `docs/DEVELOPMENT_STORY.md`, and report honestly
what passed, what you skipped and what is still broken.
