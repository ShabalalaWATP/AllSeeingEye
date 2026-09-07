# Research expansion status audit

7 September 2026. This reconciles the full expansion plan with the current
worktree. It does not replace or reduce the approved scope. Three focused
read-only reviews covered E0–E5 and E8–E13; the implementation owner checked
E6–E7. Source files and tests were inspected, rather than treating old unchecked
boxes as proof that a feature is absent.

**Implemented locally** means the relevant path exists with supporting tests.
It does not mean a real provider, operator database, GPU workflow or model-quality
gate has been accepted. The full objective remains unfinished.

## Current verification

- Saved-map image packaging now has local implementation and targeted acceptance:
  82 distinct backend cases, 30 frontend integration cases and 29 engine/capture
  cases passed, followed by final regression and static checks. See
  `SAVED_MAP_IMAGE_EXPORT.md`. Actual browser/GPU acceptance remains open after
  browser policy verification denied tab access. Earlier historical notes about
  image export being absent are superseded by this entry.


- Selected-original retention subsequently passed 84 checks on disposable
  PostgreSQL 17.10, including real quota/consume races and migration 0027 parity,
  report preservation and downgrade refusal with retained bytes. Final SQLite
  groups passed 30 and 52 checks; frontend passed 175 tests across 37 files.
  Mypy (558 files), Ruff, architecture contracts, configured Bandit, scoped
  frontend lint, types/build, Caddy validation and file/whitespace checks passed.
  Focused independent review has no unresolved blocking findings. The disposable
  database was removed. No operator migration, deployment, coverage
  remeasurement, live model/provider or GPU acceptance was performed.
  See `SELECTED_ORIGINAL_ASSETS_IMPLEMENTATION.md` for exact scope and logs.
- After spherical clustering, the full frontend passed 852 tests in 153 files:
  95.48% statements, 90.18% branches, 94.19% functions and 96.65% lines.
- The full backend passed 2,724 tests, with 14 skips and 95.63% coverage in
  `data/identity-relationships-backend-full.log`, exit code zero.
- Subsequently, 62 identity migration/repository/service/API/team/export tests
  passed on a fresh loopback-only PostgreSQL 17.10 container, in
  `data/identity-postgres-acceptance.log`. The container was removed afterwards.
  Migration 0026 schema parity, report preservation, empty downgrade/re-upgrade
  and retained-history downgrade refusal passed. No operator database was used.
  Concurrent CAS/quota races and backup recovery remain separate acceptance work.
- The earlier backend full pass (2,623 tests, 14 skips, 94.46%) predates identity
  review and combined exports. It is historical evidence only.
- Production build, type checks, scoped lint and file-length checks passed after
  clustering. Existing import-contract checks passed before this frontend-only edit.
- Security scan `c2e2ad9e-7a7b-49b6-87ca-0f032b924516` was sealed with no findings.
  All 76 changed-source inventory paths have completed review evidence. Its sealed
  coverage remains labelled partial because the tool retained two earlier pending
  checkpoint entries; this reporting limitation is not silently treated as a clean
  complete-coverage artefact. No live provider, operator database or GPU acceptance
  was performed by the scan.
- The browser policy verification failure was reproduced on the official FIRMS
  API page. No account, API key or Gmail verification was completed. It blocks
  that onboarding workflow, not other local engineering work.

## E0–E3: sources, language and planning

Subsequent map implementation: dashboard distance/perimeter/net-area measurement
now uses GeographicLib WGS84 with bounded typed/clicked vertices on both
projections. Saved report maps now reuse the panel and layers, retaining original
coordinates and a versioned method in immutable revisions. This follows the
full-suite snapshot above. Map-image export and actual GPU drawing acceptance
are not claimed.
See `adr/0015-geodesic-measurement.md` for formula, dependency and rendering limits.
The resulting full frontend suite passed 863 tests in 158 files, with 90.11%
branch coverage. Build, scoped lint and the production dependency audit passed.

| Requirement | Implemented evidence | Remaining work |
| --- | --- | --- |
| Regional seed scenarios | `backend/evaluations/regional_cases/` contains 12 synthetic cases, four per country | Independent human labels/agreement and actual model evaluation |
| Source feasibility inventory | `REGIONAL_SOURCE_EXPANSION.md`, `SOURCE_FEASIBILITY_2026_09.md`, source catalogue; eight regional feed checks recorded | Complete source-specific access, reuse and live coverage acceptance across the proposed matrix |
| Retention and map-geometry decisions | `adr/0014-research-evidence-retention.md`; selected original re-upload, scoped quotas and expiry/deletion lifecycle | Wider source-specific capture and retain-at-import integration |
| Map hardware/browser baseline | `SAVED_MAP_VIEW_IMPLEMENTATION.md` records Intel Iris Xe, Chrome, projection and 390px fixture checks | Complete measured performance, seam/pole restoration and repeated-cycle memory acceptance |
| Shared language catalogue | `domain/languages.py`, profile schema, query preparation, `useLanguageCatalogue`; `test_language_capabilities.py` | Arabic/Persian PDF shaping; no inference that narrative support proves PDF support |
| Original scripts and matching normalisation | Matching preserves original evidence and separates Persian matching substitutions | Explicit transliteration provenance and source-calendar contract; never guess a calendar |
| Query translation and provenance | `query_translation.py`, `query_preparation.py`, retained transformations and model usage | Semantic preservation of unquoted names/negation requires representative model evaluation |
| Editable bounded collection plan | Candidate hypotheses and executable predeclared challenge/disambiguation term searches; exact source capability, shared-budget interleaving, distinct task receipts, scope reuse and exports | Model-proposed candidate/task planning and independent semantic acceptance; subject-only registry candidate routing |
| Model-proposed plan constraints | Replan proposals are bounded to allowed query changes; initial planning is deterministic | Broader validated entity/challenge planning, without arbitrary fetch URLs |
| Collection/model budgets | Quick 6 requests/45s; detailed 24/180s; shared admission across passes, separate bounded translation/replan calls | Cost/sufficiency evaluation against actual models |
| Replanning | One shared-budget review can revise an empty search or investigate cited potential conflicts; bounded sufficiency stop requires complete review context and completed explicit tasks; proposed/applied decisions and excerpts are frozen | Independent semantic conflict/query-preservation and stopping-quality evaluation; calibrated sufficiency is not claimed |
| Historical coverage honesty | Registry/RSS snapshots are disclosed; native historical providers carry capability metadata | Deeper provider-specific historical collection |
| Source administration | Persisted activation, isolated tests, derivative control, environment exclusion, session rechecks | Wider provider setup and operational acceptance, not a replacement admin workspace |

Relevant tests include `test_research_plan.py`, `test_research_run_budget.py`,
`test_query_translation.py`, `test_query_preparation.py`, `test_replan_queries.py`,
`test_research_replanning.py`, `test_source_controls.py`, `SourceControls.test.tsx`
and `AdminSourcesPage.test.tsx`. Synthetic structural tests do not prove semantic
translation quality or complete cancellation coverage at every real-model stage.

## E4–E5 and E8: geography, maps and observations

| Requirement | Implemented evidence | Remaining work |
| --- | --- | --- |
| Remove fictitious centroid incidents | `application/feeds/geo.py`, `geographicPrecision.ts`; approximate points and unlocated lists are separate | Broader visual acceptance |
| Snapshot/SSE consistency and bounds | `stores/events.ts`, reconciliation tests, `LiveCoverage.tsx`; explicit snapshot/browser bounds | Measured performance acceptance |
| Frozen evidence geometry | `domain/evidence_geometry.py`, separate observation acquisition metadata | Complete uncertainty, original CRS, exact locator and geometry review/history contract |
| Shared globe/flat rendering | MapEngine, MapLibre engine and EvidenceMapCanvas share records and state | Full projection/GPU parity |
| Private report overlays and saved revisions | ReportEvidenceMap, frozen geometry, immutable map-view domain/service/API/storage | Real GPU acceptance of the implemented image export |
| Bounded local GeoJSON import | 5 MiB, 2,000 features, 100,000 vertices and operation limits | Full seam/pole/topology acceptance |
| AOI launch and time basis | MapAreaSelection, exact saved-map launch, native AidData/Copernicus collection; publication/acquisition/project-year basis | Universal coverage is not promised; provider support remains explicit |
| Layer catalogue | Category controls, observation switches and local overlays exist | Unified descriptor/grouped-layer service and source-health/freshness presentation |
| Clustering | Existing low-zoom category aggregation; spherical-bin repair in progress | GPU acceptance and measured density behaviour; ordinary bin boundaries remain |
| Wrapped geometry and measurement | Bounded line splitting, polar preservation and GeographicLib-backed dashboard/report-map distance/perimeter/net-area measurement; saved original coordinates and versioned method | Polygon clipping/tessellation with holes, complete geodesic paths and current GPU acceptance |
| AidData | Exact project/year/recipient/AOI query and frozen provenance | Full-release compatibility/performance and operator activation |
| Copernicus | AOI/date/cloud search, original footprint/acquisition metadata | Selected original imagery, paired comparison and live acceptance |
| OONI | Country/day aggregate provider with explicit licence acknowledgement | Integrated time-chart layer and wider operational acceptance |
| IODA | Registered live connector in `adapters/feeds/cyber.py` | Desired historical research/time-series layer, usable positive-record schema and current reuse/operational acceptance |
| FIRMS | Optional NOAA-20 Area API connector, protected server-key requests, bounded CSV parsing, acquisition/quality metadata, scheduler health and both-map display controls | Administrator credential editor, actual key onboarding, live compatibility/coverage and GPU checks |
| Vessel positions | Keyless Fintraffic regional AIS adapter, bounded gzip, stable positions, 15-minute record-age expiry, direction/unknown-direction symbols and attribution; one live check accepted 681 positions; large-expiry/queue-gap snapshot recovery | Wider coverage/providers, account-based onboarding and sustained/GPU acceptance |
| ChinaPower ADIZ, AMTI and ISW layers | Discovery/reference backlog | Approved versioned dataset adapters and map presentation; no invented tracks, borders or sovereignty assertions |

The existing IODA feed must not be confused with the still-deferred IODA research
provider. Likewise, a Copernicus footprint is not retained imagery, and the optional
FIRMS adapter still needs an operator key and live acceptance. Map-image export has local implementation; actual GPU acceptance remains open despite saved map-state and evidence-package support.

## E6–E7: organisations, relationships and claims

| Requirement | Implemented evidence | Remaining work |
| --- | --- | --- |
| Companies House and SEC depth | Profiles, officers/PSC snapshots and recent SEC metadata providers | Selected filing documents/content and bounded older SEC pagination |
| Registry/designation/procurement sources | GLEIF profile/direct/ultimate parents, imported UKSL/OFAC snapshots, first-page Contracts Finder | ITA, Find a Tender and wider upstream-format/operational acceptance |
| Candidate versus reviewed identity | Migration 0026, immutable root/revisions, authorised identity service/API/editor/history and selected export; 62 focused PostgreSQL checks plus seven independent-transaction quota/CAS/revocation races passed | Wider operational acceptance and human-reviewed false-merge evaluation |
| Dated organisation assertions | GLEIF report relationship view preserves source type, dates, status and evidence | Independent immutable relationship review/disagreement annotations; do not substitute identity-match decisions |
| Claims and original evidence | Migration 0025, exact title/summary excerpts, origin metadata, proposal/review/withdrawal revisions, automatic generation and selected packages | Representative atomicity/semantic-support evaluation and deeper original-source-chain inspection |
| Separate grading dimensions | Doctrine/grading/assessment code and tests preserve A–F, 1–6, confidence and likelihood roles | No single truth percentage or politically assigned grade is authorised; new pathways require the same checks |
| Corrections and audit | Claim and identity history, CAS, quotas, current access and final export rechecks | Relationship-specific review and wider operational acceptance |

The GLEIF period omission repair applies to future collections. Frozen historical
reports retain their original, potentially understated counts. Existing canonical
report evidence and source attributes remain the authority for the new display.

## E9–E13: preservation, media, daily use and release

| Requirement | Implemented evidence | Remaining work |
| --- | --- | --- |
| Version comparison | `application/reports/comparison.py` compares structured report/evidence/assessment fields | Claim/identity revision comparison and a dedicated evidence-linked confidence-change explanation |
| Selected retained assets | Exact-version re-upload matched to frozen original SHA-256; migration 0027, permitted-use declarations, personal/team/global reservations and quotas, scoped UI/download/delete, periodic expiry and bounded tombstones | Explicit retain-at-import and permitted source-specific original retrieval; operational backup/recovery acceptance |
| Evidence packages | Frozen report/receipts/locators, hashes, exact annotation and original-asset selection; generated inert members and final access/lifecycle checks | Saved-map GPU acceptance; wider source-original coverage |
| Archives | Availability lookup and optional Save Page Now return a dated URL | Operator capture inventory, selected content retrieval, completeness manifest and terms-gated retention |
| Local media | Sanitised images, English OCR and three bounded timestamped video frames | Audio transcription, multilingual original/translated OCR, paired comparison and supported candidate-location annotations |
| PDF scripts | Chinese SC/TC embedded fonts and recorded round-trip/visual checks | Arabic/Persian shaping and visual/text-extraction acceptance; keep current warnings |
| Personal research library | Private report favourites/tags/notes and separate saved maps | Unified exact saved-view and reproducible research-preset workflow |
| Meaningful-change schedules | Evidence/hash/flag/support/confidence/validation comparison, opt-in and unchanged/replay suppression | Claim/identity revision-aware changes, substantive assertion comparison and richer explanations |
| Broader subjects | Bounded OpenAlex/Crossref, Parliament and World Bank providers | Live acceptance, selected court source if pursued, deeper content/history where approved |
| Current checks | Full frontend: 863 passes after measurements; full backend: 2,724 passes, 14 skips; coherent milestones committed | New work still requires appropriate checks; live acceptance remains separate |
| Human benchmark | Synthetic seeds and evaluation harness | At least 60 independently human-labelled cases with required split/reviewer/date, measured release metrics and actual configured-model results |
| Operational release | Some historical disposable DB/browser checks | Current PostgreSQL, real provider/model, GPU, migration/recovery and privacy/export acceptance |

Meaningful monitoring is already partly implemented in `domain/research_changes.py`
and `persistence/schedule_changes.py`; it is not a missing scheduling foundation.
Original-asset retention has its own scoped lifecycle and acceptance checks,
separate from the library's privacy checks. Synthetic evaluation seeds must never
be relabelled as independent human review.

## Next engineering priorities

1. Extend PostgreSQL acceptance and preserve its exact scope in the record.
2. Complete GPU acceptance for implemented seam/pole clustering and measurements.
3. Verify rendered map-image exports and extend explicit original retention
   to eligible source-specific capture and retain-at-import workflows.
4. Extend automated candidate planning and independently evaluate implemented
   operator tasks, possible-conflict replanning and sufficiency decisions.
5. Add relationship review, claim-aware comparison/alerts and evidence-linked
   confidence explanations.
6. Add timestamped transcription, multilingual OCR and Arabic/Persian PDF shaping.
7. Complete permitted regional layers, FIRMS/vessel onboarding and source health.
8. Obtain independent human benchmark labels and complete actual model/provider,
   PostgreSQL and browser release acceptance.

These priorities organise the full backlog; they do not redefine completion.
