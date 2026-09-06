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
