# The All Seeing Eye: Proposal Overview

Status: approved by Alex on 3 September 2026 with two amendments: the 3D globe is the default view (not merely the primary one), and the logo is specifically the React Bits Evil Eye component at https://reactbits.dev/backgrounds/evil-eye. All recommendations in section 2 and in `06_OPEN_QUESTIONS.md` are now decisions of record; the ADRs are Accepted. Building starts with Phase 0. Read this first; the detail lives in the numbered documents alongside it.

| Document | Contents |
|---|---|
| `01_ARCHITECTURE.md` | System design, backend layering and ports, the unified Event model, the pipeline, the bounded live store, realtime delivery, durable data model, frontend architecture, cross-cutting concerns |
| `02_DATA_SOURCES.md` | About 120 free sources checked against their current documentation, with auth, limits, licence notes, reliability defaults and the phase in which each arrives |
| `03_DOCTRINE_AND_REPORTING.md` | How UK and NATO doctrine is encoded: the intelligence cycle as product structure, NATO grading, the PHIA probability yardstick, analytical confidence, the report templates, the generation pipeline, the validator, provenance |
| `04_FEATURES_AND_VIEWS.md` | Every view, tracker and feature with a MoSCoW priority |
| `05_ROADMAP.md` | Seven phases with acceptance criteria, plus risks |
| `06_OPEN_QUESTIONS.md` | Twenty questions with options and recommendations, and the free keys to obtain |
| `07_SECURITY_BY_DESIGN.md` | Threat model and controls |
| `adr/` | Seven proposed architecture decision records |

## 1. What we are building

A self-hosted, dark-mode OSINT fusion application. A 3D globe is the primary view, with a 2D map mode offering Ordnance Survey, satellite and hybrid base layers. Dozens of free feeds (news in many languages, conflict events, natural disasters, aviation, maritime, space, cyber, government and humanitarian sources) are normalised into one event model, graded, clustered and streamed to the globe. Trackers give focused views of conflicts, disasters, aviation, maritime, space and cyber activity. An LLM behind any OpenAI-compatible endpoint writes structured intelligence products (INTSUM, INTREP, country briefs, conflict assessments, SITREPs, warning reports and free-form answers) that use the PHIA probability yardstick, separate analytical confidence ratings, NATO source grading and citations to frozen evidence. Two roles: user and admin. Only accounts, configuration, reports and cited evidence are ever stored.

## 2. Key recommendations

Each of these is argued in an ADR or a numbered document; each is reversible until Phase 0 starts.

1. **MapLibre GL JS 6 with deck.gl** for both the globe and the map. One engine, a native globe-to-Mercator transition, free, and it takes OS Maps, satellite mosaics, NASA imagery and terrain tiles. Cesium is the alternative if true 3D ever matters.
2. **Modular monolith**: one FastAPI process (Python 3.12, uv) hosting the API, the collectors and report generation, with hard internal boundaries (domain, application, adapters, API) enforced by import linting. Docker Compose with PostgreSQL 16 plus PostGIS and Caddy.
3. **The live tier is a bounded in-memory cache, not a database.** Per-category retention windows and item caps, a global memory budget, a prune loop, an optional snapshot file. Historic questions go to the upstream APIs on demand. Long-term "normal levels" for warning rules are stored as tiny hourly aggregates. This is how the app stays small on a home machine.
4. **Evidence freezing.** When a report is generated, the items it cites are copied into durable evidence rows with hashes, capture times and Wayback archive links. Reports remain verifiable after the cache has moved on, and this is the only path from live data to permanent storage.
5. **Grade before generate.** Reliability comes from an admin-owned source registry; credibility is computed per item from corroboration, contradiction and consistency, independently of the source's reliability. The LLM receives grades as facts and cannot change them.
6. **Doctrine is enforced, not suggested.** A validator checks every key judgement for exactly one PHIA yardstick term, a separate confidence rating with the three-factor statement, resolvable citations, no hedge words, and a "what changed" line against the previous version. Reports that fail after one retry are stored as needing review.
7. **Direction is a first-class feature.** Collection plans with PIRs, SIRs and EEIs, areas of interest, and an indicators and warning board turn the NATO cycle into the product's information architecture and give the LLM well-formed questions to answer.
8. **Security by design from Phase 0**: argon2id, rotating refresh tokens, CSRF, rate limits, admin-approved account requests, object-level authorisation, SSRF guards on every outbound fetch, HTML stripping, a strict CSP, encrypted keys, prompt-injection defences at the LLM boundary, locked and audited dependencies.
9. **Feeds and APIs only, no scraping**, so the app stays polite and the licence position stays clean. The catalogue has more free sources than the first year can absorb.

## 3. What the research changed

- OpenSky moved to OAuth2 client credentials with daily credit buckets; a registered account gets about one global poll every 90 seconds, so AOI polling matters.
- The free OS Maps plan covers Road, Outdoor and Light at zooms 7 to 16 for Great Britain; tiles are proxied so the key stays server-side.
- Esri World Imagery is being retired in phases from October 2026, so EOX Sentinel-2 cloudless and NASA GIBS are the satellite defaults.
- ACLED tiers access by email domain; UCDP needs a token; ReliefWeb needs a pre-approved application name; DeepStateMap keys are by permission; Liveuamap and ADS-B Exchange are paid; X has no free tier; the Bellingcat Ukraine map is now an archive.
- The current UK yardstick is the 2025 PHIA table (seven bands with deliberate gaps), and the UK confidence framework has three named factors; both are encoded exactly.
- NATO report paragraph formats live in a restricted publication, so the INTSUM structure is a doctrine-consistent proposal rather than a copy.
- The React Bits Evil Eye installs through the shadcn CLI with a single dependency; it is a full-canvas shader, so it is paused whenever the globe is visible.

## 4. How the build proceeds

Phase 0 foundation and auth; Phase 1 fusion core and globe with about twenty starter feeds; Phase 2 grading and the first four report templates; Phase 3 the trackers; Phase 4 direction and warning; Phase 5 social and foreign-language; Phase 6 hardening and polish. Each phase ends with green CI, 90 percent coverage, updated docs and a usable product.

## 5. What I need from Alex

The answers in `06_OPEN_QUESTIONS.md`, most importantly: where it runs and who can reach it; the globe engine and database confirmations; which LLM endpoints you will use; the Telegram and scraping policies; confirmation of the doctrine specifics; and the accent colour. Everything else has a recommended default that the build can start on.
