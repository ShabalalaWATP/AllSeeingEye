# Research expansion operations

Implementation in progress on `main`, 6 September 2026. This record distinguishes
working bounded features from the wider expansion backlog. No operator database
migration, live account change, deployment or configured-model evaluation is implied.

## Research and source selection

The collection-plan preview makes no model or source calls. It enumerates the
actual registered provider inventory, supported scope and collection ceilings.
An operator can supply bounded original terms and language-specific variants.
Explicit variants are operator-authored and take precedence. At run time, missing
non-English variants can be generated in one bounded translation call using the
report's frozen team/global AI routing. The deterministic preview itself stays free
of model calls. Original terms, transformed terms, model and outcome are saved;
syntactic validation does not prove translation quality. Private document/media
inputs and empty source selections do not trigger this translation stage. Explicit
source selections govern collection; unknown identifiers fail before requests.
Changes invalidate the preview. The reporting window resolves when a run starts.

Quick collection remains six requests, 45 seconds and 200 retained items; detailed
collection remains 24 requests, 180 seconds and 800 items. General research with a configured direction model can revise an empty successful
search once. The initial pass reserves half the request allowance, and both passes
share the same deadline and unique-item cap. Nonempty initial results use remaining
requests on unattempted sources without invoking the model. A revision can change
terms and generated language variants only; source selection, dates, country and
subject remain fixed. Operator language variants are preserved. The model revision
has a maximum 20-second deadline within the remaining collection time. Both passes
and their exact tasks survive in receipts and exports. Private document/media and
non-general record research do not use this replan. The challenge pass keeps
its existing separate shared budget. Empty responses do not confirm absence.
Historical completeness is not inferred from a recent feed or current registry.

## Predeclared challenge and identity tasks

The collection editor supports up to eight candidate hypotheses and eight explicit
additional searches. Each candidate has a stable identifier, a label and optional
distinguishing identifiers. These are operator-supplied hypotheses, never verified
identity matches. An identity-disambiguation search must reference a candidate;
a conflicting-evidence search can stand alone. Search phrases are supplied exactly
by the operator and are not automatically translated or changed by replanning.

Preview the ordinary inventory first, then choose an eligible selected source for
each additional search. Only providers with explicit support for these term queries
are offered. Subject-only registry queries and area-only imagery catalogue queries
cannot silently repeat the original lookup while claiming to search another
candidate. Unsupported tasks have an explicit receipt and make no request.

Selected baseline tasks and additional searches are interleaved deterministically,
starting with a baseline task. They share the same six/24 request, elapsed-time and
unique-item ceilings, including both collection passes. No extra task allowance is
created. Large plans can have unexecuted tasks; inspect budget-exhausted receipts.
The expanded inventory is capped at 64 tasks and rejected before source requests
if larger. Task IDs keep separate outcomes when one source is queried repeatedly.

Candidate context, exact task terms, purpose and individual outcomes are retained
in the frozen report receipt and exports. Follow-ups retain this explicit scope.
Task phrases also contribute to ranking already-held context, including when a
task is unsupported or not executed. This ranking does not establish a successful
source search, a supporting relationship or a verified candidate identity.
The existing post-draft challenge stage clears these predeclared tasks so it cannot
replay them accidentally. Private document/media research does not accept public
source tasks. A candidate's absence from a search does not establish a non-match.

This implements executable operator planning. Model-generated candidate plans,
contradiction-triggered replanning and evidence-sufficiency stopping remain open.

Persian, simplified and traditional Chinese narrative preferences are available.
The catalogue distinguishes narrative scripts from supported search editions.
Persian does not invent a Google News edition. Original text and zero-width
characters are retained; Persian character matching uses a separate derived key.

## Regional feeds and public records

Eight additional publisher-discovered RSS feeds cover Russia, China and Iran.
They retain headlines, attribution, dates and links, with F6/unassessed grading.
IranWire's oldest-first feed uses bounded newest-item selection. Feed discovery,
actual smoke checks and restrictions are recorded in
[source feasibility](SOURCE_FEASIBILITY_2026_09.md).

Company research accepts `GB:01234567` or `companies-house:01234567` for explicit
UK registry queries, and `LEI:` followed by an exact LEI for GLEIF. Officers and
PSC queries share the existing Companies House credential allowance. A reported
accounting-consolidation parent is not a verified beneficial owner. Names remain
identity candidates; neither shared addresses nor missing records prove control.

Reports now include **Reported organisation relationships**, derived solely from
the selected version's frozen GLEIF parent evidence. Direct and ultimate parents
remain separate assertions. Original periods, registry status and source-reported
corroboration are shown with links to the evidence annex. Missing or unreadable
metadata remains explicit. This view does not merge identities, establish current
ownership or replace an operator relationship review. The corrected collection
omission count includes malformed and over-limit period entries; older saved
reports retain their original, potentially understated counts.

Scholarly and parliamentary metadata require explicit source selection or the
documented subject controls. OpenAlex and Crossref are overlapping aggregators,
not automatically independent confirmation. Retraction/update flags remain
attributed metadata requiring review. World Bank queries request one country,
indicator and bounded annual interval, preserving missing values separately from zero.

OONI is optional and disabled until `ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED=true`
is deliberately configured for appropriate CC BY-NC-SA 4.0 use. Country/day
counters are contributed measurements, not population coverage or proof of cause.
No individual probe locations are collected. A legacy IODA live-feed connector
already exists. The separate historical research/time-series integration remains
deferred pending usable documented records and reuse terms.

## Administrator source controls

Administration remains under `/admin` and is available only to administrators.
Sources supports persisted activation, isolated bounded connection checks and
polling-circuit reset. A connection check does not publish fetched results.
Source activation is separate from source grading and model routing.

Activation applies to live and private collection, including source derivatives.
Operator environment exclusions cannot be overridden in the UI. Research-only
sources require a research query to demonstrate coverage. Existing keyed providers
continue to use their configured server-side credentials; this slice does not
introduce per-team source credentials or a universal key editor.

Migration `0022` adds source activation records. Run normal migrations only against
the intended backed-up database. Development tests use disposable databases.

## Maps and evidence inspection

Country-only evidence no longer acquires a fictitious incident point. Approximate
city/administrative locations use hollow markers and remain separate from precise
point clusters. Findings without supported coordinates remain in a paginated list.
Live coverage counts disclose loaded records and the snapshot/browser limits.

Report maps consume the selected frozen version, never the shared live event
mirror. Both projections use the same engine. Opening a basemap discloses the
viewed area to its tile provider; no private evidence is sent as a tile payload.
Account and access changes clear the private map and GPU layers.

Local GeoJSON imports are private and unverified. Before an explicit save they are
memory-only. They require
source/date/attribution/precision metadata and are bounded by file, feature and
vertex limits. Antimeridian lines are split for display; wrapped polygons must
be supplied as valid pre-split geometry. Imports do not silently filter research
or become frozen report evidence. Reloading loses unsaved local overlays. The
saved-view implementation now uploads canonical overlays only on explicit Save,
with personal/team scope disclosure. It preserves camera, filters, selection and
immutable revision links; its final integration acceptance is tracked in
[saved map views](SAVED_MAP_VIEW_IMPLEMENTATION.md).
Polygon validation also shares a one-million-operation ceiling across an import;
overly complex files require simplification. Canonical labels survive re-parsing
and are truncated at Unicode character boundaries.

Claim inspection projects frozen judgements, assessments and citation checks.
Stable IDs identify a judgement within a version; compound statements are not
presented as automatically extracted atomic facts. Evidence support, source
independence, coverage and citation validity remain separate dimensions.

## Evidence packages

The ZIP export resolves one immutable report version and rechecks access after
rendering. It contains Markdown, structured report/evidence/analysis JSON, supported
point GeoJSON, a manifest and integrity hashes. It fetches no source URLs and
includes no original files, images or external map tiles. Null geometry preserves
unlocated findings. Source rights still apply to captured excerpts.

The package is bounded to 1,000 evidence items and 8 MiB uncompressed content,
with two admitted render workers. Hashes verify the exported bytes, not the
authenticity of the source. No signature or trusted timestamp is supplied.

## Additional bounded capabilities

Copernicus Sentinel-2 acquisition footprints can be requested from a report map
with explicit disclosure of the selected area and dates. The authenticated request
allows a non-wrapped box of at most 10 degrees per side, a 14-day interval and
20 metadata records. No imagery is downloaded. Footprints do not prove visibility,
activity or change, and remain separate from frozen report evidence.

Contracts Finder collects one bounded publication page and matches supplied terms
locally. It does not claim a complete procurement or company award history.
UK Sanctions List and OFAC SDN research use explicitly configured local snapshots:
`ASE_UKSL_SNAPSHOT_PATH` and `ASE_OFAC_SDN_SNAPSHOT_PATH`. Use
`uv run ase import-designations --help` in `backend` for the bounded CSV import.
Imports retain source hashes, dates and licence metadata and refuse to overwrite
an existing snapshot. No operator snapshot has been imported during development.
Names remain identity candidates; a name match is not a confirmed designation.

The personal research library stores favourites, tags and notes separately from
report contents. Each user sees only their own annotations and currently accessible
reports. Migration `0023` adds these records; deleting a report clears annotations.
Both new migrations refuse a downgrade that would silently discard retained data.

Chinese PDF narratives now embed renamed OFL-licensed Noto-derived SC/TC fonts,
with script-specific wrapping. Pagination and mixed dates/citations were tested,
and a generated PDF was visually inspected. Arabic/Persian shaping remains an
explicit PDF limitation; DOCX preserves original text. No runtime font downloads
or automatic translation-quality claim is introduced.

## Remaining acceptance

Saved-map API/UI integration subsequently passed all 698 frontend tests, with
95.79% statements, 90.11% branches, 94.52% functions and 96.99% lines. The full
backend run had 2,197 passes, 14 skips and six outdated-fixture failures at 96.19%
coverage; the 18 affected PDF/font/catalogue cases passed after fixture repairs.
This is a full backend run plus targeted repair verification. The saved-map
contract records disposable PostgreSQL and real Intel GPU browser checks, along
with the remaining map reproduction/export acceptance limits.

The query-replan and shared-map-foundation frontend run passed all 683 tests:
95.84% statements, 90.21% branches, 94.69% functions and 97.01% lines. Frontend lint,
type checks and production build passed. The focused final replan backend group
passed 54 cases; Ruff, mypy, import boundaries and Bandit passed. The earlier full
backend verification below predates these additions and is not a new full run.

The [implementation plan](RESEARCH_EXPANSION_IMPLEMENTATION_PLAN.md) remains the
full backlog. These features do not establish automated translation quality,
complete historical datasets, fully accepted reproducible map exports, retained original
assets, human-reviewed identity corrections or unrestricted provider coverage.
Twelve synthetic regional cases are development seeds, not human-labelled results.
Configured-model evaluation and the wider 60-case human review remain open.
Verification: the full backend run completed with 1,946 passing tests, 14 skips
and five failures. The affected suites were corrected and rerun successfully;
combined coverage after those reruns is 96.04%. This is a full run plus targeted
repair verification, not a second full backend run. Additional disposable migration
checks passed. The final frontend run passed all 654 tests: statements 95.79%,
branches 90.13%, functions 94.64%, lines 96.97%.

Ruff, mypy (461 source files), import boundaries, configured Bandit, frontend lint,
type checks, formatting, production build and file-length checks passed. Staged
Gitleaks checks passed. Python and frontend dependency audits found no known
vulnerabilities (the local application package is not a PyPI audit target).
The production build retains a bundle-size advisory. Browser QA verified both
projections, no horizontal overflow at 390 pixels, and canvas removal on close.
No operator database, deployment or real-model evaluation was performed.
