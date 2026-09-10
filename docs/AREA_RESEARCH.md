# Research an area from the main map

Implemented 10 September 2026. The **Research area** button on the right-hand
map toolbar opens a compact 360 px drawer in both globe and flat-map modes.

## Operator flow

1. Draw a polygon, rectangle or circle. Rectangles and circles support dragging
   or two clicks. Completed areas can be moved, redrawn or cleared.
2. Optionally enter a question. Leaving it blank requests a neutral overview of
   the available evidence, developments, uncertainty and gaps.
3. Choose the last 24 hours, 3, 7 or 14 days. Detailed collection is the default;
   Quick uses the existing smaller research budget.
4. Check sources. This local capability preview makes no provider or model
   calls. It shows supported sources, unsupported capabilities, the fixed UTC
   interval and request, item and collection-time limits.
5. Confirm disclosure and generate the report. The configured AI connection
   performs the existing evidence assessment, citation checking and report flow.
   Progress and cancellation remain visible. Closing or changing tools cancels
   the request; a report already being saved may still complete.

The result opens in personal Reports. It retains the exact canonical geometry,
server-calculated hash, interval and collection receipts. Its evidence map starts
with that boundary. A saved map view can subsequently use the existing saved-area
research flow. Regeneration preserves the original boundary and interval.
Ordinary follow-ups cannot silently drop the spatial scope.

## What collection covers

The source catalogue is not an assertion that every entry can search a polygon.
The flow checks the existing registry and uses selected supported capabilities
within the existing budget. Display-layer switches do not limit research, and
research does not switch those layers on.

- **Retained public feeds:** reads enabled public feed data already held by the
  server, including precise point records for conflicts, news, hazards, aircraft,
  vessels, satellites and other event categories. Original source IDs, URLs,
  grades and timestamps survive into evidence and citations. This is not a
  fresh external search, historical backfill or guaranteed current position.
- **Copernicus:** the existing external scene-metadata query supports a single
  axis-aligned rectangle of at most 10 degrees per side and a suitable interval.
  It does not analyse imagery or widen another shape to a rectangle.
- **Fresh USGS and EONET searches:** one dated catalogue request per selected
  source, followed by exact local polygon/multipolygon intersection. USGS uses
  earthquake origin time; EONET uses dated original event geometry and includes
  open and closed events. At most 50 Quick or 100 Detailed candidates and a
  14-day interval. Question terms do not filter these observations. Provider
  bounding-box/page limits mean overlapping or older records can be omitted.
  Fresh records precede retained duplicates; original source identities remain.
- **Other capabilities:** unsupported scope and collection failures are recorded.
  The configured AidData historical-project flow uses its recorded-year policy;
  this recent-area drawer does not activate that mode. CCTV imagery, camera
  directories and infrastructure catalogues are not searched by the retained
  event provider.

Retained-feed selection checks exact polygon membership, including split
multipolygons and holes. Country-only, approximate, ungeolocated and unsupported
footprint records are excluded. Dates use observation acquisition time where
present, otherwise publication time. Unknown dates are excluded. Source and
category sampling prevents traffic volume from consuming the whole allowance.
Legacy EONET records without validated original incident point geometry are
excluded because a displayed polygon centre is not an exact incident location.
Most conflict/news records only have city, regional or country precision and
therefore do not qualify for exact-area selection. This is a coverage gap,
not evidence that the area has no conflict. The new 21 publisher headline
capabilities serve ordinary question research and do not claim polygon support.
Receipts state missing categories, exclusions and truncation. Empty results do
not establish absence of activity; model output does not establish complete
collection or independently verified facts.

## Bounds and access

- Drawing retains at most 32 points. Circles use 32 perimeter points and a
  maximum 1,000 km radius. Dateline rectangles are split exactly; crossing
  polygons/circles request a rectangle instead of guessing another area.
- Direct-area input is limited to 16 KiB and 256 vertices. Server-side canonical
  validation rejects invalid topology, extra features and non-area geometries.
  No supplied fetch URL is used.
- Geometry, question or period changes invalidate preview and disclosure.
  Obsolete requests abort. Account, role and workspace changes clear private
  state and suppress late navigation or result delivery.
- Drawing, research, measurement and RF placement have one active map-input
  owner. Research layers have distinct IDs and do not intercept evidence picks.
- The retained provider scans at most 2,000 candidates per category through
  cooperative work outside the API event loop. It selects at most 88 Quick or
  264 Detailed records with fair source/category sampling. Global collector
  request, item, duration and cancellation limits remain in force.
- The retained capability and original sources pass current administrator
  controls before release. Report access is checked before collection and again
  before persistence. No new database or dependency is introduced; only selected
  frozen report evidence is persisted.

The existing plan and report endpoints accept
`research_area: { geometry: <GeoJSON FeatureCollection> }`. A saved-map origin and
a direct area are mutually exclusive. Preview returns the canonical area and
hash. Generation still requires `disclose_area_to_provider: true`.

## Validation limits

Automated tests cover both projections using a mocked engine, drawing input
ownership, exact scope replay, source failures, cancellation, access changes,
geometry validation, regeneration, source controls and bounded selection.
Interactive browser/GPU acceptance remains unavailable under the existing
administrator browser-control policy. Configured-model report quality and
exhaustive real-world source coverage are not established by these tests.

Frontend validation: the broader run passed 1,839 tests with one existing skip.
Coverage was 95.45% statements, 90.69% branches, 93.45% functions and 96.63%
lines; unchanged gates passed. A final 43-test area-specific run passed after
the last presentation and lint corrections. Full frontend ESLint, application
and tooling TypeScript, production build and changed-file formatting passed.
Existing vendor-chunk and untouched MapLibre file-length warnings remain.

The local API was restarted on port 8001. Health returned 200, the served
OpenAPI includes both direct-area inputs, and unauthenticated plan/report
requests returned 401. The ASE frontend on port 5174 returned 200.

Backend validation: 189 affected tests passed in 4 minutes 11 seconds, with
93.49% combined statement/branch coverage across seven area/request/provider
modules and the normal 90% gate. Full Ruff, formatting, mypy and import-linter
passed. Changed-source Bandit and independent security/correctness reviews
found no actionable findings. Eight follow-up frontend regressions also passed,
including the direct-area scope guard.

The whole backend suite was stopped at about 5% after twelve minutes because
repeated app/database setup made it an hours-long run. No failures had been
observed; full-suite backend coverage is not claimed.
