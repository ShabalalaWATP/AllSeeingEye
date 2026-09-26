# AidData regional project research implementation contract

Implementation status, 7 September 2026: the local catalogue, historical research
forms, native provider, spatial filtering and frozen report integration are built
in the working tree. Full regression and targeted fixture repairs are recorded below; operational
acceptance remains pending.
This extends E8 without replacing the remaining research expansion workstreams.

## Current delivery and remaining gates

| Capability | Current evidence |
| --- | --- |
| Native import and bounded local search | Parser/import/search fixtures pass; nine pinned upstream projects parsed successfully across the recorded smoke checks |
| Historical country and saved-area research | API creation/regeneration fixtures pass, including exact older map revision |
| Project facts and money | Original years, constant-2021-USD amount text, geometry, hashes and licences retained |
| Spatial correctness | Hole, boundary, false-envelope-match, scan-past-limit and deadline regressions pass |
| Operator controls | Year forms, preview invalidation and consent reset have component integration tests |
| Exact project identifier lookup | Implemented in follow-up working tree; exact lookup integration tests pass, review pending |
| Year-only retrieval ranking | Neutral-recency relevance fix in working tree; regression passed, review pending |
| Whole-release compatibility and performance | Not established; small bounded source samples do not prove these |
| Real-browser globe/flat-map acceptance | Still required for the new project workflow |
| Real configured-model research quality | Still required; integration tests use a scripted model |
| Full regression and commit | Milestone committed as 0a48040; follow-up lookup/ranking changes are uncommitted |

The chronology below records when individual foundations were delivered. Its older
statements of outstanding work describe that stage, not the current status.

## Verified upstream contract

- GeoGCDF v3.0.1 resolves to commit
  `0ed90518dddfef9a39acfe45716148b5700d478b`.
- Individual project GeoJSON is available under that immutable commit, avoiding
  the mutable `main/latest` path in frozen provenance.
- The inspected project 35756 contains a MultiPolygon and project identifiers,
  recipient, title, amount in constant 2021 USD, status, sector, commitment year,
  implementation/completion years and date strings. One inspected project is not
  evidence that every project uses this exact shape.
- Bulk release archives are approximately 496 and 551 MB compressed. They must
  not be fetched by an ordinary per-question collection request.
- AidData describes original data as ODC-By and OSM geometry as ODbL, with
  attribution to both. Preserve separate licence metadata and source references
  in UI, frozen evidence and exports; do not label the whole package permissively.
- The data describes historical Chinese financing commitments and associated
  projects. A project status is a dated source assertion, not a current finding.
- The pinned feature-methodology README explains that points and lines are
  buffered by approximately one metre, then dissolved into MultiPolygons with
  other project features. Some road features derive from generated driving
  directions. The displayed polygon therefore cannot be described as a measured
  project boundary, construction extent or accuracy radius. Preserve this
  transformation method in geometry provenance and operator-facing limitations.

Evidence: `aiddata-feasibility-probe.json`; upstream README and release:
https://github.com/aiddata/gcdf-geospatial-data/blob/main/README.md
https://github.com/aiddata/gcdf-geospatial-data/releases/tag/v3.0.1
https://github.com/aiddata/gcdf-geospatial-data/blob/0ed90518dddfef9a39acfe45716148b5700d478b/examples/features_intro/README.md

## Required semantics

1. Introduce typed project metadata, separately from satellite ObservationMetadata.
   Retain dataset/release/project identity, recipient, reported status, monetary
   units/base year, source field names and temporal precision.
2. Preserve year-only dates as years. A comparison interval from the beginning of
   that year to the beginning of the following year is a computational bound,
   never a claimed January observation. Do not infer exact precision from a
   January 1 string without upstream methodology establishing it.
3. Keep commitment, implementation and completion as separate temporal roles.
   Missing dates remain unknown; no publication or retrieval substitution.
4. Use explicit interval-overlap predicates for year-precision filtering, with
   visible wording that an overlap is possible within the reported year. A
   narrow query cannot establish that the commitment happened during those days.
5. Support explicit full-year project queries. Keep source-specific ceilings:
   extending project history must not expand Copernicus's 14-day query allowance.
6. Existing frozen reports and saved map revisions keep their original time
   semantics. New metadata must be optional and absent from legacy canonical
   payloads. A new saved time basis must be explicit, versioned and validated.
7. Use PROJECT_SITE geometry with upstream precision retained. Approximate/admin
   geometry is never promoted to a precise incident location. Handle mixed
   precision conservatively, and retain unlocated records in evidence lists.
8. Preserve independent publication, dataset release and collection times.
   Rank year-known projects without rewarding an invented exact date.

## End-to-end delivery

- Bounded, versioned reference dataset ingestion outside the shared event store,
  with checksum/size/schema/geometry checks and explicit source provenance.
- Search project identifiers, recipient and terms locally over the admitted
  dataset; spatial selection respects original geometry and precision.
- Report preview exposes dataset release, temporal basis, limits and truncation.
  Source activation and current access checks apply before and after collection.
- Collection and selection share the same temporal predicates; the report freezes
  metadata and geometry. No CURRENT_RECORDS or acquisition-timestamp workaround.
- Both map projections and timelines show project site, year precision, release
  and licence; all report/evidence/export surfaces preserve those distinctions.
- An operator can ask a project question or select an area and full-year window,
  inspect returned records and obtain a cited report without manually entering
  project IDs for every search.

## Acceptance cases

- Commitment year overlaps query year, disjoint years excluded, exact upper
  boundary excluded; unknown commitment year disclosed rather than fabricated.
- January 1 values without precision evidence remain conservative year precision.
- Reported completion is not disbursement; constant-USD amount is not nominal USD.
- Same project/release deduplicates, different releases retain reproducible
  provenance, a newer source release never mutates old report evidence.
- Mixed precise and administrative geometries retain uncertainty in both views.
- Buffered/dissolved source polygons remain labelled as derived project geometry;
  the buffer distance is not a confidence radius or evidence of project width.
- Oversized, malformed, duplicate-key, invalid-coordinate and unsupported records
  yield bounded failure or explicit omissions, never silent fabricated geometry.
- Cross-team access, source disable during collection, cancellation, export
  licence notes and legacy hash compatibility are verified.
- Real source smoke checks and operator/model acceptance remain separate from
  deterministic fixtures and unit test success.


## Implementation record

The project metadata foundation is in progress. Immutable domain records now retain
source identities/hash, recipient, attributed status, geometry precision, licences
and nullable commitment/implementation/completion years. Capture and strict frozen
codecs preserve metadata, omit absent additions for legacy evidence hashes, and
expose it through the report API and frontend runtime parser. Evidence JSON,
GeoJSON, prompt/export provenance and event memory accounting include the fields.

Fifty-five focused backend project, observation and package tests passed. These
include legacy hash compatibility and the API serialisation boundary. This does
not implement source ingestion, temporal overlap filtering, project-year query UI,
financial-field semantics or project evidence display. Those remain required for
the complete adapter. No source is activated by this foundation.


### Project evidence inspection and temporal precision foundation

Project details now appear in the report evidence annex and selected-map evidence,
including unknown/year-only dates, historical reported status, attribution and
separate data/geometry licences. Geometry-only evidence uses a source-geometry
heading. React renders supplied source strings as text. Code-point-aware frontend
bounds preserve valid non-BMP Unicode accepted by the backend.

The project temporal helper distinguishes unknown dates, disjoint intervals,
possible partial-year overlap and a query covering the whole reported year.
Its bounds are computational uncertainty bounds, never occurrence timestamps.
Collection, query forms and map timeline policies are not yet wired to it.

Read-only review found and prompted fixes for Unicode encoding, frontend/backend
length disagreement and project text bypassing instruction-pattern screening.
Selection now screens project strings; direct prompt rendering suppresses flagged
project text while exports retain the original. Sixty-three focused backend tests
and twelve frontend tests passed. Ruff, mypy (492 source files), architecture and
scoped Bandit checks passed; final integration and adapter delivery remain pending.
No source activation, dataset import or operational acceptance is implied.


### Native AidData parsing and atomic reference catalogue

The native GeoGCDF parser retains year-only dates, mixed source precision, exact
Decimal amount text labelled constant 2021 USD, derived project geometry and a
SHA-256 of the original bytes. A supplied January 1 date does not fill an unknown
commitment year. Native filename/record identity, duplicate keys, bounds and
malformed fields are checked. Extreme decimal years are rejected before integer
expansion.

A separate SQLite reference catalogue can now be built from a directory of native
project GeoJSON files. It indexes country/year and searchable text, enforces file,
byte and record bounds, and publishes a content-addressed name atomically without
overwriting existing data. Invalid imports publish no partial catalogue. File
identity is checked after opening and before reading. Windows tests exposed and
fixed connection-close cleanup and DirEntry stat identity differences.

Thirty-four combined native parser/catalogue/project tests passed; Ruff, mypy
(494 source files) and scoped Bandit passed. A live fixed-commit project 35756
smoke check parsed 24,822 bytes with SHA-256
`a6996a4bfbc70a8bffcb5c786f1ce20d0e383b8c8e576ea423f49c7c5e8a9a10`.
It retained commitment year 2011, amount `39390602.4479984` constant 2021 USD and
MultiPolygon geometry. This single-record smoke check does not establish whole
release compatibility. No operator dataset was imported or source activated.

The import function still needs its operator CLI/admin wiring, read-only bounded
query adapter, provenance/financial facts propagated into Events and frozen
metadata, and year-policy integration through collection and both map views.
The full expansion objective remains active.


### Bounded catalogue search and operator import command

`uv run ase import-aiddata <directory> --cache-dir <destination>` now exposes the
native local import. It explicitly does not activate a source or change the
application database. Read-only searches apply all supplied terms, recipient
country and year bounds, returning at most 20 records with truncation disclosure.
Unknown years require explicit inclusion. SQL uses bound values, including a JSON
term array; returned records are decoded and checked against their search indexes.
Deadline, catalogue, row and aggregate result-size bounds apply.

Review prompted fixes for extreme Decimal token errors, ignored coordinate-system
declarations, file check/open replacement and whitespace normalisation mismatch.
The importer now rejects explicit outer CRS declarations, uses bounded numeric
parsing and verifies a regular opened handle against the pre-open identity before
reading (with no-follow/nonblocking flags where supported). Missing whitespace-only
source text consistently becomes Unknown. Tests cover each finding and failure
cleanup. Twenty-nine adapter/import/search tests passed; mypy passed across 496
source files. Source discovery/activation, provider routing, financial metadata
capture and year-aware report/map policies are still pending.


### Explicit recorded-time policy for project evidence

A new `recorded_time` policy matches project commitment-year uncertainty intervals,
uses acquisition for other observations and publication for reporting. Existing
publication/acquisition policies keep their prior semantics. ResearchQuery exposes
an optional explicit policy; the collector, temporary event store and frozen
receipt now preserve it. Final selection can use the same policy without creating
an occurrence timestamp. Project year starts are comparison keys only.

Saved-map API/runtime schemas accept the explicit new policy. Both projections
share the year-overlap filter. Timeline choices use year-end query cut-offs, while
evidence labels say commitment year and exact date unknown. Unknown project years
follow the unknown-date control, never publication or retrieval fallback. Coverage
and export text explain possible partial-year overlap.

Thirty-one focused backend time/store/legacy tests and thirteen frontend map/time/
coverage tests passed. Backend Ruff, mypy and architecture checks passed. Frontend
types passed and scoped lint passed after correcting two redundant conditionals.
Report creation/preview must still carry the explicit time policy, admit bounded
project-year windows and wire the catalogue provider. These changes alone do not
establish an operational end-to-end AidData research workflow.


### Historical project request and provider integration checks

Report creation, collection queries and plan previews now carry an explicit
recorded-time policy. Historical project requests require fixed dates and preserve
the ordinary map/publication defaults. Preview and creation share the exact
10,980-day ceiling; a one-microsecond overrun is rejected without day rounding.
The local AidData provider is registered through existing source controls and
retains original geometry, project provenance and exact constant-2021-USD amount
text. Missing catalogues return unavailable, not an empty successful search.

Two focused backend groups passed 38 cases each (six provider cases overlap):
native parsing/search/time behaviour, provider records and request bounds, and
planner/replanning compatibility. Ruff passed and mypy passed across 497 source
files. OpenAPI and frontend types were regenerated. These checks do not establish
whole-release import compatibility or an operational end-to-end historical form.
Historical form controls, geographical catalogue queries, broader integration
verification and source activation remain unfinished. The changes are uncommitted.


### Operator historical project controls

General research now offers recent reporting or a fixed commitment-year range.
Both end years are included, up to 30 complete years. Historical requests omit the
rolling window, carry recorded_time, and require a current preview with a selected
supported source. Year edits invalidate preview; a response with changed dates or
time policy is rejected. Changing to a different research focus restores recent
reporting. Copy distinguishes recipient country, commitments and current activity.

The focused frontend group passed 19 tests covering year validation, collection
plans and existing area research. A subsequent mismatched-policy regression passed
with all seven collection-plan tests. Type checks, scoped ESLint and file-length
checks passed before that final test-only addition. No real-browser or configured
catalogue/model acceptance is claimed. Financial detail presentation, spatial
catalogue querying and broader backend report integration remain outstanding.


### Native historical report integration and financial inspection

HTTP tests now use the real provider composition with a disposable native catalogue,
source admission and SQL report persistence. Preview retains recorded_time and
recognises the selected provider. Creation and regeneration preserve year-only
project metadata, source geometry, exact amount text and fixed report dates while
keeping publication unknown. Private results do not enter the shared event store.
Persisted source disabling suppresses evidence; ordinary follow-up requests cannot
silently discard the historical policy. The model remains a deterministic fixture.

Eleven combined historical/area creation and regeneration cases passed. The later
preview assertions passed in both native historical cases. Backend Ruff, mypy
(497 source files) and both architecture contracts passed. The shared map/evidence
project panel now displays exact reported amounts labelled constant 2021 USD;
four UI tests passed, including zero, unknown and long fractional values. Scoped
UI lint passed. Read-only integration review is pending; no live catalogue/model
acceptance, source activation or commit is implied.


### Historical scope review repairs

Read-only review identified three integration gaps. Historical forms now default
to explicit AidData selection and require a supported selected AidData task; a
news-only preview cannot substitute for project research. Recorded-time collection
no longer imports unsolicited live-feed context. The single-provider challenge
pass preserves that provider's explicit source ID, allowing native catalogue
counterevidence searches. Ordinary source selection and the shared challenge
budget remain intact.

Both backend regressions failed before their fixes. Eighteen combined provider,
challenge, historical HTTP and area-generation tests then passed. Eight frontend
collection-plan tests passed, including deselecting AidData and selecting news.
Backend Ruff and mypy (497 source files), frontend type checks and scoped ESLint
passed. Review verification of the repairs remains pending. These changes are
uncommitted; spatial catalogue queries and full expansion acceptance remain open.


### Exact project-area search foundation

The read-only catalogue search now accepts an optional exact ResearchArea and
filters full source polygons before applying the 20-result cap. It scans beyond
nonmatching candidates, with a shared byte budget, catalogue row ceiling, deadline
checks and an aggregate 200,000-vertex allowance. Byte-limited searches disclose
truncation; exhausted work or invalid geometry fails instead of claiming a complete
empty result. Missing geometry does not match an area.

Shapely 2.1.2 supplies topology validation and intersection predicates in the
adapter layer, with its dependency and typing package locked. This avoids applying
the annotation validator's 256-vertex ceiling to source boundaries. Holes are
respected, boundary contact counts as intersection, and invalid topology or unsplit
seam crossings are rejected without repairing or changing source coordinates.
The upstream API reference is https://shapely.readthedocs.io/en/stable/_reference.html .
This is planar source-geometry overlap, not proof of site activity or geodesic area.

Thirteen spatial/catalogue tests passed, including a match after 21 nonmatching
records, holes, boundary contact, invalid geometry, seam rejection and total vertex
limits. Mypy passed across 498 source files; scoped Ruff, file-length and diff
checks passed. The local dependency audit found no known vulnerabilities (editable
application package excluded). Provider spatial admission, saved-area historical
form wiring, native-release performance and broader acceptance remain pending.
The prior three integration fixes were verified read-only with no remaining
confirmed blocker. No source activation, operational import or commit occurred.


### Project provider spatial admission and saved-area form

AidData now declares area support for explicitly selected recorded-time project
queries and forwards the exact ResearchArea into catalogue search. The provider
retains full geometry and reports planar overlap limitations. Native provider
collection verifies an intersecting area and excludes a nonintersecting triangle
whose envelope overlaps. Nine provider tests passed.

The saved-area form now offers historical commitment years alongside its existing
acquisition/publication interval. Historical mode selects AidData, preserves exact
map IDs, submits recorded_time and complete-year dates without a rolling window,
and resets preview/consent when years change. Existing observation queries retain
the 14-day allowance. Seven area UI tests passed, including the new historical
submission; the earlier combined area/general-plan group passed 14 tests before
that addition. Ten backend spatial/native-HTTP compatibility cases passed.

Backend Ruff/mypy (498 source files), frontend type checks/scoped ESLint,
file-length and diff checks passed. Spatial review, combined saved-area native
historical HTTP/regeneration acceptance and real-browser/performance checks remain
pending. No operational source activation, import, deployment or commit occurred.


### Saved-area native historical HTTP verification

The native catalogue HTTP tests now cover both country research and an exact
saved polygon, with the source enabled and disabled. They preview, create and
regenerate against disposable SQL persistence. A newer map revision cannot change
the explicitly selected historical area, and regeneration retains geometry,
commitment dates, monetary text and recorded-time policy. Area tests correctly
omit country scope, matching the existing standalone area contract and UI.

Spatial review identified final-row deadline accounting: Python/GEOS work could
finish after the deadline without another SQL/loop check. A deterministic test
failed before the fix; the search now checks the deadline before releasing any
result, including an empty result. Eighteen combined spatial, catalogue and HTTP
cases passed after the fix. Ruff and mypy across 498 files passed. Full regression
runs are the next gate; no commit or operational acceptance is claimed yet.


### Full frontend regression completion

The unchanged AidData frontend completed all 775 tests in 138 files, terminal
exit 0: 95.68% statements, 90.09% branches, 94.59% functions and 96.88% lines.
Backend source/new-test formatting checks and both architecture contracts passed.
The repository-configured full-source Bandit scan passed. An earlier unconfigured
invocation reported the already documented B101/B105 low-severity categories;
the CI command explicitly loads their existing pyproject policy. No new exclusions
were added. Backend full regression is still live under session 59672, with log
at data/aiddata-backend-full.log. No terminal result or commit is claimed.


### Additional pinned-release source smoke

Eight further native projects were fetched from the immutable release commit and
parsed successfully: 100, 1577, 20443, 2416, 30518, 31302, 32627 and 34105. They
cover eight recipient codes and geometry sizes from 5 to 622 vertices. The probe
retained result metadata, byte sizes and source hashes in the ignored artifact
`data/aiddata-release-sample.json`; no project catalogue was imported or activated.

Sampling selected eight evenly spaced entries from GitHub's bounded 1,000-entry
contents listing. It is not a random or representative sample and does not prove
whole-release compatibility, approximate/admin geometry coverage or performance.
The backend regression remains live under its original session; source was not
edited during these read-only upstream checks. The frontend production build also
completed successfully with the existing bundle-size advisory.


### Contract audit during the frozen backend run

Two remaining delivery gaps were confirmed by reading the current implementation.
`aiddata_search.py` matches only its title/recipient/sector index; it does not yet
provide the promised exact project-ID lookup. Add an explicit bounded identifier
filter through search/provider/UI, with a test showing that an exact ID matches
without appearing in the title and that partial or malformed IDs are not aliases.

`selection.py` returns zero retrieval score for all year-only projects because
`evidence_time` correctly returns no exact timestamp. This also makes its existing
term-count multiplier ineffective among project records. Implement relevance-first
project ordering without inventing an occurrence date or changing doctrinal grades;
verify better keyword matches and deterministic ties with identical year precision.
These are pending code changes, not reasons to reinterpret the current full suite.
The source remains frozen until the live regression run terminates.


### Isolated preparation while regression runs

Two prospective changes are drafted under ignored data/aiddata-next, not installed
in application source. The search draft adds a bound exact project_id parameter
and checks returned identity. A disposable two-project probe verified exact lookup
without title inclusion, rejected partial matching, retained recipient filtering,
and rejected malformed, oversized, injection-like and non-ASCII IDs.

The ranking draft gives admitted year-only project records neutral recency while
preserving credibility/reliability weights and the existing keyword multiplier.
Direct checks confirmed a nonzero project retrieval weight, unchanged unknown-date
behaviour for ordinary evidence, and continued absence of an exact timestamp.
These are preparatory checks, not integrated selection or API/UI acceptance.
Both drafts passed Ruff using backend configuration. Integration and proper
regression tests remain required after the unchanged full backend run finishes.


The isolated ranking probe now exercises actual selection over two project events,
not just arithmetic. Current selection chose ID a (one matching keyword); the
draft chose ID z (two matching keywords), while retaining both records, unknown
publication dates and unchanged source reliability. The executable probe is
data/aiddata-next/check_ranking.py. It remains preparatory, outside production.


### Full backend regression and targeted fixture repairs

The full unchanged backend run terminated with 2,430 passed, 14 skipped and three
failures in 1,309.12 seconds, with 95.98% coverage. The failures were test expectation
updates: the source inventory omitted AidData, and two incomplete-map-ID cases
expected application rejection even though request construction now rejects them
first. Dedicated construction assertions replace those two cases; resolver tests
retain the other invalid-scope checks. All 21 affected tests passed afterwards.
This is a full run plus targeted repairs, not a second clean full suite. Coverage
is the measured full-run value; the repair run used --no-cov.

Frontend verification remains 775 passes with coverage thresholds satisfied and
a successful production build (existing bundle-size advisory). Static/type checks,
architecture, configured Bandit and dependency audit results are recorded above.
The integrated AidData milestone is ready for final pre-commit gates. Exact-ID
lookup and relevance ranking are isolated follow-up drafts and are not included.
Whole-release, real-browser and configured-model acceptance remain outstanding.


### Exact lookup and relevance follow-up, after 0a48040

The integrated AidData milestone was committed to main as 0a48040 after all
pre-commit gates passed. The working tree was clean and no remote was configured.
The next uncommitted slice integrates exact project lookup and relevance ranking.

An optional Project ID field adds an explicit aiddata:<digits> constraint to the
frozen research terms, using the existing preview/request/receipt contract. Native
search binds the ID as an exact SQL value and retains other terms, recipient,
year and polygon filters. Partial IDs are not aliases; malformed/multiple IDs are
unsupported. Both ordinary historical and saved-area report/regeneration tests
exercise the identifier path. Model replan and challenge term changes retain the
selected project ID and reject substitution of another ID.

Year-only project records now receive neutral retrieval recency so the existing
keyword and source weights can rank them. A regression failed before the change
and passed afterwards, selecting the stronger keyword match despite opposite ID
order. This is retrieval priority only: publication stays unknown, and source and
judgement grades are unchanged. Ordinary undated records retain prior behaviour.

Focused backend groups passed 18 lookup/ranking/provider cases, 17 native-HTTP/
lookup/ranking cases and 27 lookup/replan/challenge cases (groups overlap and later
groups follow the model-scope changes). Seven area UI tests passed with exact ID
submission. Frontend type checks passed before the last test-only edit; scoped
ESLint, final Ruff, mypy (499 files), file-length and diff checks passed. Read-only
review and final integrated checks remain pending. No new full coverage run or
follow-up commit is claimed; prior full verification belongs to 0a48040.


### Exact lookup receipt and preview verification

Read-only review found that challenge collection preserved the selected project
ID while its top-level receipt retained only model-proposed terms. Two regression
cases failed before the fix. Receipts now use the effective validated query terms
passed to collection, including the project ID. The regression covers successful
and failed redrafts and exhausted-source receipts. Review found no remaining
concrete issue in this fix.

The area UI regression now changes, removes and restores the project ID after
preview. Each edit invalidates the preview, clears disclosure consent and disables
submission until a fresh preview and consent are supplied. All seven area UI tests
passed. The combined lookup, ranking, native HTTP, replan and challenge backend
group passed 59 tests. Ruff, mypy (499 source files), frontend type checks, scoped
ESLint, file-length and diff checks passed. These are focused checks without a new
coverage measurement. Whole-release catalogue performance, configured-model and
real-browser operational acceptance remain open. No source activation, operator
migration or deployment was performed.
