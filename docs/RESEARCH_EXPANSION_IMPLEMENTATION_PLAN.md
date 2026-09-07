# Research expansion implementation plan

Prepared 6 September 2026 against `60f57e4` on `main`.
Status: partially implemented. The bounded delivery milestone and outstanding
acceptance are recorded in [research expansion operations](RESEARCH_EXPANSION_OPERATIONS.md).
The workstreams below retain the full target scope; a delivered subset does not
mark an entire workstream complete.
This is the next expansion plan. Earlier delivered work remains in
[the automated research plan](MASTER_AUTOMATED_RESEARCH_PLAN.md).

Companion specifications:
- [Current implementation and acceptance audit](RESEARCH_EXPANSION_STATUS_AUDIT.md)
- [Russia, China, Iran and shared source matrix](REGIONAL_SOURCE_EXPANSION.md)
- [Globe and flat-map implementation](GEOSPATIAL_RESEARCH_PLAN.md)
- [Saved map-view persistence and acceptance contract](SAVED_MAP_VIEW_IMPLEMENTATION.md)
- [Area-based research collection contract](AOI_RESEARCH_IMPLEMENTATION.md)
- [Current product direction](OSINT_PRODUCT_DIRECTION.md)

## 1. Outcome and boundaries

An operator can ask a question about an event, organisation, claim or place,
obtain relevant public records and reporting, inspect supporting and contrary
evidence, and receive a report with a reproducible map and clear limitations.
Russia, China and Iran receive dedicated coverage presets, languages and source
adapters. Selection follows the research question, not a desired political result.
Official statements, independent reporting and technical observations remain
separate evidence roles. Teams provide sharing, access and lightweight comments.

Keep the existing FastAPI/React modular monolith, administrator-only workspace,
Evil Eye branding, default globe, flat-map toggle and free feeds/APIs-first policy.
No paid service, scraping pipeline or new hosted database is assumed. Unsupported
sites remain reference links or authorised manual document imports. No bypass of
paywalls, access controls or platform restrictions is part of this plan.

## 2. What already exists and what must deepen

| Existing capability | Expansion needed |
| --- | --- |
| Bounded quick/detailed research, challenge and collection receipts | Explicit query planning, translated queries, source capability routing and historical coverage |
| Frozen evidence, citations, source chains, scoring and reports | Structured claim ledger, reviewed identity decisions and evidence packages |
| Companies House profile/search and SEC recent filing metadata | Officers/control/filing documents, corporate parent records, procurement and designation records |
| Translation, supplied-document/media extraction | Persian support, Chinese script distinctions, transcripts and stronger verification workflow |
| Report versions, follow-ups and schedules | Claim-level corrections, historical comparisons and useful personal research library |
| Shared MapLibre globe/mercator renderer | Geometry, uncertainty, scoped research overlays, temporal layers and real GPU parity checks |
| Source catalogue and admin AI connections | Source activation/test workflow, licence/coverage status and connection health |
| Synthetic evaluation harness | Representative human-reviewed benchmark and actual configured-model evaluation |

Meduza English, TASS English, SCMP and Nikkei already exist as outlet seeds.
Do not count them as new integrations. The source catalogue includes unimplemented
candidates and old host probes; both require explicit status in the expansion.
Country-only evidence can currently be rendered at a country centroid as if it
were a located event. Geographic precision is a prerequisite, not a cosmetic extra.

## 3. Operator experience

1. Enter a question, organisation identifier or place; optionally select Russia,
   China, Iran or a custom region preset. Presets select defaults, never evidence grades.
2. See interpreted entities, time window, languages, source families and estimated
   collection/model budget. Correct ambiguity or choose a specific registry match.
3. Run bounded collection with cancel, partial results and source-specific receipts.
4. Read Answer first; use Evidence, Timeline, Map and Connections on the same result.
5. Select a sentence to inspect its claim and supporting/contrary excerpts. Select a
   connection or map feature to see the same frozen evidence and its limitations.
6. Follow up, save privately, share with a team, compare with an earlier version,
   export an evidence package, or opt into meaningful-change monitoring.

The existing globe remains `/`. Improve Research navigation and contextual actions
instead of replacing the home view. Research result tabs are not new independent
copies of data. Unlocated findings remain available in the evidence list.

## 4. Sequenced work packages

Effort sizes express relative complexity, not promised dates: S is a focused
change, M spans an adapter/API/UI slice, L spans several boundaries and evaluation.
All items below are initially unchecked. Owners are engineering responsibilities,
not a request to create permanent teams in the product.

| ID | Work and owner | Depends on | Size | Completion evidence |
| --- | --- | --- | --- | --- |
| E0 | Baseline fixtures, source feasibility and architecture decisions, lead/backend | None | M | Current suites recorded; source status reviewed; benchmark examples agreed |
| E1 | Language and query contracts, backend/frontend | E0 | M | Persian and Chinese-script round trips; no invented locale coverage |
| E2 | Source controls and regional feeds, adapters/admin UI | E0, E1 | L | Tested permitted sources in each preset, unavailable receipts and shared-origin deduplication |
| E3 | Research planner and capability router, application/UI | E1, E2 | L | Editable bounded plan actually governs requests, cancellation and costs |
| E4 | Geographical precision foundation, backend/map UI | E0 | M | Country-centroid false precision removed in both projections |
| E5 | Shared evidence map and timeline, map UI/backend | E3, E4 | L | Scoped overlays, AOI research and projection parity accepted |
| E6 | Organisation records and identity resolution, adapters/application | E3 | L | Companies House/GLEIF/designation/procurement dossier with dated sourced edges |
| E7 | Claim ledger and quality dimensions, application/report UI | E3 | L | Support/opposition/origin chains inspectable, existing scoring preserved |
| E8 | Regional dataset and observation overlays, adapters/map UI | E2, E5 | L | Licence-approved dated layers, no inferred tracks or false precision |
| E9 | History, preservation and evidence packages, storage/reporting | E5, E7 | L | Bounded retained selections, safe exports and temporal reproducibility |
| E10 | Media verification and multilingual documents, media/reporting | E1, E5, E7 | L | Transcript/frame citations, paired comparisons, tested Unicode/RTL export |
| E11 | Library and meaningful-change monitoring, frontend/application | E7, E9 | M | Saved results, scoped comparisons and evidence-based notifications |
| E12 | Broader subject adapters, adapters | E3, E7 | M | OpenAlex/Crossref, Parliament, World Bank and optional court material |
| E13 | Model evaluation, operational checks and release, QA/security/lead | Starts E0; final all | L | Human-reviewed quality results, migration drills, GPU/browser/security checks |

Recommended first release: E0-E5 plus the initial E7 claim inspection. It delivers
regional source presets, better search and credible maps before the larger graph,
archival and imagery work. E6 and E7 then form the organisation-research release.
E8-E10 form the historical/geospatial verification release. E11-E12 broaden daily
use. E13 supplies a release gate to every slice, not only the last one.
E4 can run alongside E1/E2 after E0; a single owner integrates
shared schemas, container wiring, generated API types and migrations.

### E0: establish facts and decisions

- [ ] Create 12 seed research scenarios, four per country, spanning official claims,
  organisation identity, multilingual reporting and geographic uncertainty.
- [ ] Inventory actual adapters, runtime prerequisites, allowed use and source
  origin relationships. Probe only normal public endpoints without credentials
  in logs; record date/status/content type, not just HTTP 200.
- [ ] Write ADRs for selected evidence retention, private map geometry and regional
  dataset caching. Default raw live-store ephemerality remains unchanged.
- [ ] Record actual hardware/browser baseline for maps; preserve current 5,000-event
  client bound and collection limits until measured changes justify revisions.

### E1-E3: collection and language

- [ ] Introduce a shared language capability catalogue consumed by profile schemas,
  research forms, source adapters, prompts and exports. Add `fa`; distinguish
  simplified/traditional Chinese and explicit regional search editions.
- [ ] Preserve original script, original dates, transliteration and translation as
  different fields. Normalise Persian/Arabic character variants for matching only;
  preserve zero-width characters and original evidence. Calendar conversion needs
  an explicit source calendar; ambiguous dates remain ambiguous.
- [ ] Translate query terms deliberately, preserving identifiers, names and quoted
  phrases. Store the query variants and transformation provenance in receipts.
- [ ] Represent a bounded ResearchPlan with question, candidate entities, source
  tasks, language variants, temporal/AOI scope, budget and challenge tasks.
- [ ] Validate model-proposed plans against allowlisted adapters and enum/schema
  constraints. Models never supply arbitrary fetch URLs or execute code.
- [ ] Keep existing six-request/45-second quick and 24-request/180-second detailed
  collection ceilings initially. Plan/translation/model budgets are separately
  counted; shared-origin tasks and retries consume the same admitted budget.
- [ ] One bounded replan can address empty/contradictory results. Stop on explicit
  budgets or sufficient evidence; absence is an unsuccessful search, not confirmation.
- [ ] Add historical intervals only for adapters that support them. A year-long
  request must not silently use a recent RSS snapshot as complete history.
- [ ] Add tests for negation, transliterated names, identical names, unavailable
  scripts, prompt injection in source text and cancellation during each stage.

### E6-E7: entities and claims

- [ ] Extend Companies House with permitted officers, PSC records and selected filing
  documents; extend SEC with selected filed content and bounded older pagination.
- [ ] Add GLEIF reported parent relationships, UK/OFAC primary designations, ITA
  screening records and Contracts Finder/Find a Tender records.
  GLEIF profile, direct and ultimate accounting-parent adapters are already wired.
  A dedicated frozen-evidence relationship view now displays their original
  dates, status, corroboration assertions and evidence links. This does not
  complete independent relationship review or the other listed source work.
- [ ] Store organisation identity candidates separately from reviewed matches.
  Prefer registration number, LEI and jurisdiction over string similarity.
  Report-scoped review storage, migration 0026, authorised API and report interface
  are implemented locally. Candidate snapshots retain original identifiers and
  attributes, while operator decisions append separate history. Exact identity
  revisions can be selected alongside claims for a frozen evidence package.
  Broader acceptance, full coverage and PostgreSQL verification remain open;
  see [identity review delivery](IDENTITY_REVIEW_IMPLEMENTATION.md).
- [ ] Relationship assertions carry type, time validity, source/evidence references,
  review state and disagreement. Shared addresses are not ownership edges.
  The GLEIF report view preserves captured source assertions without inferring
  current validity, transitive edges or identity matches. Independent relationship
  review/disagreement annotations remain outstanding.
- [ ] Claim ledger uses stable IDs and atomic assertions, support/opposition excerpts,
  original-source chains, inference labels and unresolved conflicts.
- [ ] Keep A-F source reliability, 1-6 information credibility and the current
  judgement/likelihood policy separate. No political-alignment grade or uncalibrated
  single percentage of truth. Any policy change requires its own version and tests.
- [ ] Display evidence support, source independence, coverage and citation validity
  as separate dimensions. New personal preferences cannot modify these policies.
- [ ] Add operator corrections with audit history and source references. Corrections
  do not rewrite previous frozen reports or train a model automatically.

### E9-E12: deeper verification and routine use

- [ ] Extend existing version comparison with added/withdrawn evidence, changed
  claims and why confidence changed. Preserve valid-time and collected-time.
- [x] Save only deliberately selected permitted records/assets, with retention and
  size quotas. Do not turn this into a historical copy of every live feed.
  Selected original re-upload now matches an internal import's frozen original
  hash, with an operator permitted-use declaration, scoped quotas and expiry.
  Wider source-specific retrieval and retain-at-import remain follow-ups, as
  recorded in `SELECTED_ORIGINAL_ASSETS_IMPLEMENTATION.md` and the status audit.
- [x] Evidence package: report, manifest, source URLs, exact cited excerpts/locators,
  permitted selected files, hashes, licence notes and collection receipts.
  Selected originals join exact annotation revisions with bounded manifests and
  final access/lifecycle checks. Exact saved-map image export remains open.
- [ ] Archive support first discovers dated captures. Retrieval is gated by archive
  terms; missing captures and incomplete content remain explicit.
- [ ] Add bounded local transcription with timestamped excerpts, frame comparison,
  original/translated OCR and candidate-location annotations. Model suggestions
  remain leads until supported; no automated authenticity score.
- [ ] Fix PDF Unicode/RTL through a reviewed font and shaping solution before
  promising Persian/Arabic/Chinese export. Retain current warnings and alternatives
  until visual and text-extraction tests pass. Keep English canonical judgements.
- [ ] Personal library: tags, saved views, recent research and reproducible presets.
  Teams add scoped sharing/comments, without assignments or operational staff workflows.
- [ ] Extend existing schedules with claim/evidence changes and user notification
  preferences; no alert for unchanged reruns or unverified causal conclusions.
- [ ] Add literature/retraction, parliamentary, macroeconomic and permitted court
  adapters using the same contract, not bespoke disconnected dashboards.

## 5. Contracts, persistence and migration approach

Proposed objects: SourceCapability, ResearchPlan, ClaimAssessment, EntityCandidate,
RelationshipAssertion, EvidenceGeometry, MapView and EvidencePackageManifest.
These are design names, not new dependencies or final generated DTOs.

Use application ports, concrete adapters and container composition. Route handlers
remain thin. Frontend features share through components/lib/stores. Generate types
from exported OpenAPI. Keep hand-written modules below the repository size limits.

Prefer versioned optional additions to frozen report scope/evidence JSON for plans,
claims and geometry. Use dedicated scoped records only when independent lifecycle,
querying or annotations require them. Do not create a global people graph.
Proposed tables, if validated in E0, are source configuration, scoped saved map views,
scoped relationship/annotation records and selected asset manifests. Public regional
datasets use a separately bounded, versioned reference cache, not the event database.

Allocate migration revisions from the actual current Alembic head during each slice;
head at planning is `0021`. Test upgrade with legacy reports and old profile defaults,
SQLite and supported PostgreSQL, safe restart, and explicit loss-sensitive downgrade.
No operator migration or destructive retention change is performed by this plan.

## 6. Administrator source controls

Under `/admin`, Sources gains source catalogue, connection setup, test, sample
receipt, activate/disable, last success, freshness, rate limit and licence status.
Credentials are encrypted server-side and shown masked; UI never returns saved keys.
Use existing global/team assignment patterns where provider terms permit them.
Provider activation is separate from changing a source reliability assessment.

A public feed may populate the existing shared event bus. A private query, keyed
team connector, upload or saved research overlay must retain its access scope.
Default source pools are public no-credential sources; external query disclosure
and provider access requirements are visible before using optional connectors.

## 7. Acceptance and security gates

- [ ] Behaviour suites, formatting, lint, types, build and 90% existing coverage gates
  pass. Add cases for stale sessions, cross-team geometry/exports and account switches.
- [ ] Retain SSRF URL/DNS/redirect validation, bounded decompression/parsing, credential
  origin binding and cancellation. No tokens in external tiles, URLs, logs or reports.
- [ ] Derived claims/maps retain the parent's scope; shared SSE never receives private
  evidence. Purge scoped client caches on logout, expiry and `access.changed`.
- [ ] Private map annotations are redacted/generalised in shared exports when needed;
  do not map witnesses' home addresses or probe-level identifying details by default.
- [ ] Record source/source-chain dependence, historic coverage, translated meaning and
  contradictory primary records in the human-reviewed benchmark.
- [ ] Expand to at least 60 labelled cases, including 12 per country and 24 cross-topic
  or adversarial cases. Separate development and held-out cases; no live facts hidden
  in supposedly immutable fixtures. Record dataset date, reviewer and uncertainty.
- [ ] Report citation-support precision, identity false merges, contradiction recall,
  abstention, coverage, latency and cost with sample sizes. Proposed first gates:
  zero known unsupported severe allegations/false identity merges in the release set,
  at least 95% supported factual citations and at least 90% seeded contradiction recall.
  These are acceptance targets, not measured app performance or universal guarantees.
- [ ] Real configured-model evaluation, live permitted source smoke checks and real GPU
  map tests pass before that capability is marked operational. Scripted tests alone
  cannot satisfy these gates. See the map plan for detailed projection acceptance.

## 8. Risks, cut lines and release record

| Risk | Planned response |
| --- | --- |
| Source lacks an API/feed or permission | Reference/manual import until access is verified; do not block unrelated sources |
| Poor regional coverage or translation | Show gaps, revise query plan and evaluate original-language examples |
| Coordinates falsely imply precision | E4 before new overlays, precision labels and no invented location/radius |
| Copyright/licence limits on maps or archives | Track permission per layer/export; disable export or use reference links |
| Dataset update mistaken for live conditions | Freeze release/observation dates and indicate stale or superseded material |
| Map scale exceeds browser budget | Bounds/LOD, server aggregation and tile delivery only after measurement |
| Larger retention exceeds local-first limits | Quotas and opt-in selection; separate ADR and storage budget before rollout |
| Model cost or provider outage | Admission budgets, partial results and explicit failure; no silent provider switch |

Each slice closes with changed behaviour, tests, measured quality where relevant,
source activation status, migration notes, docs and a coherent commit. Main remains
the user's integration branch; do not force-push or deploy. No remote is configured
at planning. Source licensing, optional keys and benchmark review are concrete
external prerequisites, not blanket permission requests for routine development.
