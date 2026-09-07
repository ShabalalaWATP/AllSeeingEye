# Research from a selected map area

Status: area selection, spatial admission and authorised exact-map plan previews
implemented locally; research launch and native provider integration remain unfinished.
This extends the full research and geospatial plans; it does not replace their
polygon, regional dataset, imagery or historical comparison requirements.

## Operator flow

Select or draw an area on a report map, inspect its coordinates and save the map.
Choose Research this area to open a new research form bound to that exact map
revision. Show the area, parent report version, destination personal/team scope,
source capabilities and requested observation dates before collection starts.
Changing the area requires a new saved revision. Do not put private geometry in
query strings or browser persistence. The launch URL carries opaque view/revision
identifiers and the server resolves their current authorisation.

The initial selection control can support a two-corner rectangle and a numeric
keyboard alternative. Using the viewport captures its bounding envelope, which
must be labelled as such rather than an exact visible-ground polygon. Reuse the
existing canonical geometry validation and saved `aoi` field. Keep arbitrary
validated polygon storage; individual providers advertise the shapes and extent
limits they can actually search. A provider's narrow limit must not become a
permanent global AOI limitation.

## Spatial collection contract

Country selection is not polygon search. Add explicit spatial capability to the
research provider inventory, plan tasks and receipts. Distinguish native bounding
box/polygon queries, bounded filtering of supported source coordinates, and sources
with no spatial coverage. Each plan must explain what its area constraint means.

Strict area mode executes only supported tasks. Unsupported tasks remain visible
with an explanation and make no requests. A later optional contextual-search mode
must label its results as context and keep them separate from observations inside
the area. Do not silently convert an AOI to a country name or fabricate a place
name through reverse geocoding. Empty results do not demonstrate an empty area.

The existing Copernicus footprint search is the first available native-bbox seam:
it admits a non-wrapped box of at most 10 degrees per side, a 14-day acquisition
interval and 20 catalogue records. Integrate it through the bounded research
provider contract. Preserve acquisition dates, cloud metadata, collection/item
identifiers and source references. Catalogue metadata does not mean imagery has
been downloaded, inspected or found to contain an event.

Broader area research still requires the planned regional datasets and additional
spatial providers. Unsupported sources must never appear supported simply because
the initial catalogue adapter works. Seam-crossing AOIs need split-query admission,
deduplication and shared budgets before their collection capability is enabled.

## Exact origin and scope

Add an optional map-origin reference to research requests and plan previews. Resolve
the saved view and exact revision through fresh access checks. Freeze its canonical
AOI, geometry hash, view/revision identifiers, exact parent report-version identifier
and revision content hash in the new report's scope/receipts.

The destination must retain the origin's personal owner or team. Administrator
access is not permission to copy another person's private map into a different
scope. Recheck origin access and destination eligibility after external work and
before persistence. Revocation or deletion must prevent delivery of derived data.

Do not use the ordinary parent follow-up path: it resolves the latest parent and
automatically seeds its evidence. An AOI origin is provenance, not permission to
admit every parent record into the new area query. Likewise, frozen report source
IDs are not necessarily callable provider IDs. Map publication filters are not
satellite acquisition dates; the form must request the appropriate interval.

## Pipeline changes needed

- Extend `ResearchQuery`, provider capability metadata and plan schemas with
  explicit spatial scope; regenerate API types through the normal exporter.
- Forward capabilities through the controlled-provider wrapper and retain source
  activation checks before collection and final release.
- Register a research adapter around the existing guarded Copernicus search.
- In strict area mode, prevent the current global live-context copy from injecting
  out-of-area evidence. Add separately tested spatial eligibility before reusing it.
- Do not rely on `Job.bbox` alone: current production selection filters event
  points, whereas valid catalogue footprints can have no event point.
- Keep bounded canonical footprint provenance outside generic event attribute
  strings, which have a 500-character value cap. Never invent a centre-point event.
- A term-only replan cannot improve a fixed catalogue box/date query. Suppress
  ineffective retries and retain shared request, duration and item ceilings.
- Add map selection/launch controls through shared components, without importing
  one frontend feature into another or changing the default globe renderer.

## Required evidence

Tests must prove exact revision binding after a newer save, scope isolation,
revocation during collection, area/date propagation into real adapter requests,
unsupported-task non-execution, no global-context leakage and bounded retries.
Exercise absent geometry, oversized areas, seam/pole cases and catalogue records
without point coordinates. Frontend tests cover keyboard selection, unsaved edits,
preview invalidation, scope disclosure and account-change aborts. Real browser
checks must demonstrate selection on both projections. Fixture success does not
establish a provider's operational availability or complete geographic coverage.

## Implementation record, 7 September 2026

Report maps now accept numeric rectangles, a labelled viewport envelope and two
map-click corners. Clicks populate a draft for review; Apply/Discard is required
before saving. Existing arbitrary AOIs remain intact until explicitly replaced or
cleared. Date-line rectangles use canonical split multipolygons, and wider numeric
rectangles retain their selected span rather than acquiring a provider-specific
global limit. Selecting or applying an area makes no research request or upload.

The research domain and saved plan receipts retain canonical area geometry and its
hash. Providers need an explicit synchronous spatial-capability hook; ordinary
country support does not qualify. Unsupported area tasks make no requests. Both
admission wrappers forward the capability. Legacy plans default to no area and no
spatial capability; previews and saved plan views can explain provider limitations.

The report application can resolve an exact saved map reference into frozen origin
metadata, enforce matching personal/team scope and recheck the origin after model
work under the final write guard. It rejects automatic parent-evidence seeding,
ambiguous linked scope and undisclosed area collection. Strict-area collection
does not copy the global live store. Term-only translation, replanning and contrary
collection are disabled for this initial spatial contract; evidence review remains
available and contrary-search limitations are explicit.

This application contract is not yet exposed as a research launch input. Authorised
preview fields now resolve exact saved map references without collection or model
calls. The next slice must add create fields and form navigation, integrate a
native spatial provider, and retain catalogue footprint provenance without
misrepresenting acquisition time as publication time or scene coverage as an event.
API creation/regeneration/session-revocation tests remain required before claiming
that operators can run area research. The wider polygon/provider/imagery backlog
remains unchanged.

Focused checks passed: 75 spatial-contract/planner/collector tests, 34 challenge
tests, 16 origin/isolation tests, 31 area/map UI tests and 11 plan UI/parser tests.
These groups overlap and are not an aggregate unique-test count. Mypy, formatting
and scoped lint checks passed. Broader integration verification is recorded when
complete in the development story.

The integrated backend group passed all 99 tests. An additional composed
application test passed for area-derived report creation and regeneration after
a newer map revision, retaining the original map origin and excluding global
context. This is an application test with synthetic providers, not HTTP launch
or live catalogue acceptance. The full frontend suite passed 715 tests in 126
files: 95.82% statements, 90.14% branches, 94.70% functions and 97.01% lines.

A synthetic Chrome harness exercised actual map rendering: two globe clicks
created a reviewed draft and a visible outline; a flat-map viewport envelope
produced a matching outline; a numeric antimeridian area saved as split polygons.
There was no horizontal overflow at 390 pixels. Access invalidation removed both
canvases and private controls. Fixture API responses were used, so this does not
establish real provider collection, full seam/pole acceptance or performance gates.

## Exact-map preview and evidence integration follow-up

The plan endpoint accepts saved map/revision identifiers and the destination team,
never client-supplied geometry. It checks current access, matching personal/team
scope and revision integrity, then returns the canonical area and frozen origin
alongside actual provider capabilities. Ordinary previews remain compatible.
Preview does not require or record external-disclosure consent because it makes
no external calls. Collection still requires explicit consent independently.
The frontend parser preserves this origin for the forthcoming launch form.

The native catalogue integration must introduce typed observation metadata and
source geometry on events and frozen evidence. Acquisition time, actual publication
time, retrieval time and report snapshot time must stay separate. Missing publication
time must remain missing. Collection and selection need an explicit acquisition
time basis for catalogue observations; retrieval time cannot admit an out-of-window
scene. Prompts, timelines and exports must label the temporal basis accurately.

Retain original bounded footprint coordinates even if display topology is unsupported.
Do not truncate to the local annotation polygon limit or create an event centroid.
Geometry bytes count towards private-store and export quotas. Frozen evidence and
package JSON should share one canonical serializer. Absent new fields must not change
legacy evidence digests, because saved-map integrity checks already depend on those
digests. Regression acceptance must cover old map hashes plus footprint/time
roundtrips through collection, selection, persistence and evidence-package export.

### Retained source geometry foundation

Events and frozen evidence now carry optional immutable source geometry and
observation metadata. Source geometry supports bounded WGS84 points, lines and
polygons, including multipart forms, without replacing coordinates to satisfy
annotation-display limits. It records an explicit location role, precision,
method, source attribution and canonical hash. Observation metadata records
acquisition/processing times, catalogue identity, scene cloud percentage and
limitations. These additions remain absent on legacy evidence records.

Snapshot/persistence roundtrips and evidence packages preserve full coordinates
and metadata. Package JSON uses the persistence serializer; GeoJSON prefers
retained source geometry to any legacy point and labels its role. Geometry counts
towards private-store estimates. Export rejects excessive aggregate geometry
before materialising JSON trees, then encodes each member and the manifest within
the remaining 8 MiB allowance. A pinned pre-extension digest verifies that legacy
saved maps remain valid.

This completes retention/export foundations only. Nullable actual publication
times, acquisition-based collection and ranking, evidence API/UI presentation and
native provider registration are still required before catalogue observations can
enter automated area research. Provider content hashes must include geometry and
observation changes, so updates cannot disappear behind an unchanged text hash.

### Acquisition-based collection and selection

Strict area research now filters and ranks observations by their acquisition time;
other area reporting uses publication time. The store, collector and final report
selector share that explicit basis and an inclusive start/exclusive end interval.
Retrieval time cannot supply recency or admit an out-of-window observation. Area
research does not apply the current-registry historical-window exception, and its
final selection does not discard footprints through a point-only bounding-box filter.
Ordinary research retains publication-based selection.

Receipts freeze `time_basis` independently of an optional plan. Drafting prompts,
text exports and the coverage UI explain the actual basis; old receipts continue
to mean publication time. Individual evidence text labels acquisition and processing
times and scene cloud percentage without injecting coordinate arrays or freeform
source metadata into prompts. Unknown processing/cloud values remain absent.

Nullable actual publication times across all existing event/report consumers,
evidence geometry/observation API and map presentation, native provider registration
and the operator launch workflow remain unfinished. These foundations do not mean
that an operator can yet run a live catalogue-backed area investigation.

### Unknown publication dates

Event, frozen evidence and research timeline publication dates now allow null.
Serialisation and exports preserve null without substituting acquisition or
retrieval time. Quality summaries use only known publication dates. Report text
and frontend date formatters show unknown; map publication-day filters do not
convert null into an epoch date. Normal feed timestamp construction is unchanged.

Undated records do not count towards publication-window activity, temporal
clustering/context or automatic archive requests. Unbounded event lists retain
them. Explicit private document/media selection can include unknown dates without
admitting unrelated public records; ordinary and area research retain their date
constraints. Synthetic area report creation/regeneration preserves acquisition
metadata while keeping publication null.

Focused backend and frontend checks passed after a test conversion-method fix.
The full backend suite passed 2,307 tests with 14 skipped and 96.13% coverage.
Full-source Bandit passed. All 720 frontend tests in 127 files passed, with
95.83% statements, 90.17% branches, 94.70% functions and 97.01% lines.
The frontend production build passed with the existing large-bundle advisory.
Native provider registration, observation API/map presentation and research launch
remain outstanding.

### Catalogue adapter preparation during verification

A draft adapter and eight synthetic contract tests have been prepared under the
ignored `data/native_area/` directory while the production source tree remains
frozen for the full backend run. The tests pass with the backend pytest
configuration. Draft adapter lint and type checks also pass. This is preparation,
not a registered provider or live-source acceptance.

The draft forwards exact rectangular area and acquisition dates to the existing
bounded catalogue port. It preserves unknown publication dates and original
geometry, distinguishes empty from unavailable results, reports truncation, and
rejects oversized or partly malformed pages without releasing partial evidence.
Content hashes change with coordinates, acquisition time, cloud metadata or
licence, while retrieval time alone does not change them.

Integration must first retain typed original geometry in `Footprint` and its
STAC parser, then register the adapter through the existing source controls.
Required integration checks include guarded HTTP request parameters, source
disable races, acquisition interval boundaries and frozen report roundtrips.
The draft tests use a synthetic catalogue port and do not prove these boundaries.

The subsequent parser, HTTP, admission and collection tests bring this isolated
group to 22 passing cases. They retain Polygon/MultiPolygon type and original coordinates,
preserve a 301-vertex footprint through frozen evidence, enforce the inclusive
start/exclusive end interval and reject unsupported geometry metadata. Mocked
HTTP composition verifies the fixed catalogue host, exact bounding box and dates,
one-request limit, redirect refusal and omission of private question/term/language
text. Domain/parser draft type checks pass. DNS validation itself is replaced by
a recording stub in these fixtures; no live network or production registration
is established. Synthetic source-admission tests verify disabling before a call
and during an in-flight result, with no scene evidence released. Actual planning
and collection tests verify explicit source selection and acquisition filtering.
Persisted source-control races and actual container integration remain open.

### Native catalogue registration

The reviewed adapter and parser are now integrated into production source. The
existing `research-copernicus-footprints` identity participates in planning and
collection through the same source admission instance and environment exclusions
as other research providers. Unsupported scopes remain explicit. Original source
geometry is an optional backwards-compatible addition to the footprint record;
the existing standalone footprint display contract remains unchanged.

Forty catalogue tests, 23 catalogue/planner/source-control compatibility tests and
three actual-container wiring tests passed. The wiring tests use persisted SQL
activation, suppress collection before disable and suppress release when disabled
during collection. They verify that private results do not enter the shared store.
Type checks cover 488 source files; both architecture contracts and scoped Bandit
passed. A read-only draft review found no confirmed blocker. HTTP responses remain
mocked, so this does not establish live-source acceptance.

Observation/geometry API presentation, footprint rendering from frozen report
evidence and the authorised operator launch form are still required. Registration
alone does not make the complete area-investigation workflow available in the UI.
