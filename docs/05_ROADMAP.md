# Roadmap

Status: proposal. Phases are sized for a hobby project with Claude Code doing most of the typing; each phase ends with green CI, coverage at or above 90 percent, updated docs and a tagged release.

## Phase 0: Foundation (1 to 2 sessions)
- Monorepo layout, `uv` backend, `pnpm` frontend, `justfile`, pre-commit, GitHub Actions, Docker Compose (api, db, caddy), `.env.example`.
- FastAPI skeleton with the layered structure, settings, structured logging, health endpoints, Alembic baseline.
- Auth: argon2id, access plus rotating refresh tokens, CSRF, rate limiting, lockout, roles, audit log; login, request-account and forgotten-password flows; first admin created by a CLI command.
- SPA shell with dark theme, routing, generated API client, login page with the Evil Eye background.
- Docs: README, ADRs 0001 to 0006, SECURITY.md, DEVELOPMENT_STORY.md, MASTER_IMPLEMENTATION_PLAN.md.

Acceptance: a user can request an account, an admin can approve it, the user can log in and see an empty globe.

## Phase 1: Fusion core and globe (2 to 3 sessions)
- Event model, pipeline stages, in-memory store with budgets and pruning, SSE stream, layer registry.
- Starter connectors (no key or free key): USGS earthquakes, EMSC, GDACS, NASA EONET, NASA FIRMS, OpenSky, one ADS-B v2 connector pointed at adsb.lol and airplanes.live (military list plus AOI radius queries), GDELT GEO and DOC, Google News RSS editions, curated outlet RSS set (about 60 outlets in 15 languages), GOV.UK FCDO travel advice, US travel advisories, UN press, CISA KEV, NOAA SWPC; ReliefWeb once its application name is approved.
- Globe with base layers, projection switch, layer manager, nation filter, country panel v1, day/night terminator, lite mode, coordinate readout.
- Source registry seeded from YAML; admin source page with health.

Acceptance: live earthquakes, fires, flights and geolocated news on the globe within one minute of start; memory stays within budget over 24 hours.

## Phase 2: Grading and reporting (2 to 3 sessions)
- Grading engine (reliability from registry, credibility from corroboration rules), story clustering, grade chips everywhere.
- LLM gateway with profiles, admin LLM page, structured output with validation, citation verification, yardstick and confidence linting.
- Templates: INTSUM, INTREP, Country Brief, Ask the Eye. Evidence freezing, Wayback archiving, report reader, Markdown export, version history.

Acceptance: generate a Country Brief for any country from live evidence; every key judgement carries a yardstick term and a confidence level; every citation resolves to frozen evidence.

## Phase 3: Trackers (3 to 4 sessions)
- Conflict tracker with UCDP (token), GDELT conflict events, ISW public layers, air-raid alerts, HDX HAPI aggregates, WHO outbreak news, the Bellingcat archive import, and ACLED if the account tier allows event-level data; conflict assessment template.
- Disaster tracker with cyclones, volcanoes, NWS/MeteoAlarm, tsunami bulletins; SITREP template.
- Aviation module: military filters, community aircraft database, emergencies, GNSS interference heat map, baselines.
- Maritime module: AISStream boxes at chokepoints, Global Fishing Watch events, NAVAREA and ASAM warnings.
- Space and cyber modules.

Acceptance: each tracker has a board, a detail view, a globe layer and a report template.

## Phase 4: Direction and warning (2 sessions)
- AOIs, collection plans and PIRs, PIR tagging in the pipeline, indicators board, alert routing (in-app, email, webhook), scheduled reports, ops room mode.

Acceptance: an indicator fires on synthetic data within one pipeline cycle and produces an alert and a report.

## Phase 5: Social and foreign language (2 sessions)
- Bluesky, Mastodon, Reddit, YouTube RSS, Telegram public channels (option chosen in the open questions), language detection, batched translation with caching, watchlists, burst detection.

## Phase 6: Hardening and polish (2 sessions)
- Optional TOTP for admins, PDF and DOCX export, report diffing, semantic search over reports, performance passes, accessibility audit, backup and restore scripts, documentation pass. The implementation uses bounded JSON vectors with SQLite/PostgreSQL parity instead of pgvector; see [ADR 0008](adr/0008-bounded-report-search.md).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Free APIs change terms or disappear | Connectors are isolated plugins with fixtures; the registry can disable a source in one click; nothing else depends on a specific source |
| Rate limits and fair use | Polite intervals, conditional requests, per-source budgets, shared caching, a descriptive User-Agent with contact |
| LLM hallucination | Evidence-only prompting, citation verification, yardstick and confidence linting, gaps section, visible grades, human review banner |
| Prompt injection via feed content | Untrusted-data framing, delimiter isolation, instruction-like text detection, no LLM tools with side effects, output schema validation |
| Geoparsing errors put news in the wrong place | Confidence levels shown on the map; GDELT GEO for pre-geolocated news; gazetteer limited to populated places; country-level fallback |
| Memory creep in the live store | Hard budgets, prune loop, admin visibility, alert when above 80 percent |
| Windows development friction | Docker for PostgreSQL; server-side ReportLab/python-docx exports avoid an office installation for generation; visual DOCX verification still needs an office renderer |
| Scope creep | MoSCoW list in `04_FEATURES_AND_VIEWS.md`; every phase ships something usable |

## Revision, 5 September 2026

After Phases 0 to 2 shipped, every candidate feed was fetched live (see `02_DATA_SOURCES.md` section O) and the plan was reordered around what answers without a key. Phase 3 now runs in three slices: 3a the tracker framework with the disaster and conflict trackers, their products and the globe upgrades they need (icons, clustering, a time slider); 3b aviation, which turned out to be far richer without keys than assumed (area-of-interest civil traffic, emergencies and the GNSS interference map all come from adsb.lol and anonymous OpenSky); 3c maritime warnings, space and cyber, with AIS and Global Fishing Watch behind their free keys. Phase 4 builds direction and warning on the tracker signals and the hourly baselines that 3b introduces. Phase 5 must re-check Bluesky, which refused this host, and keeps Telegram out per decision 7. The checklists live in `MASTER_IMPLEMENTATION_PLAN.md`.
